"""
Orchestrator for course-wide content improvement suggestions.
"""
import json
import logging
import uuid
from pathlib import Path

from openedx_ai_extensions.processors import LLMProcessor, OpenEdXProcessor
from openedx_ai_extensions.xapi.constants import EVENT_NAME_WORKFLOW_COMPLETED

from .session_based_orchestrator import CourseSessionOrchestrator

logger = logging.getLogger(__name__)


class ContentSuggestionsOrchestrator(CourseSessionOrchestrator):
    """
    Orchestrator that reviews a whole course's actual content via
    OpenEdXProcessor.get_location_content (called with the course ID), then
    asks an LLM to propose content improvement suggestions per unit.

    The full suggestion list (with section/subsection/unit ancestry) is
    always persisted course-wide in the session. What gets *returned* to a
    given request is filtered by the caller's location: no location (or a
    location outside the course tree, e.g. the course outline page) returns
    everything; a specific section/subsection/unit location returns only
    the suggestions under that node.
    """

    @property
    def _schema_path(self):
        return (
            Path(__file__).resolve().parent.parent.parent
            / "response_schemas"
            / "content_suggestions.json"
        )

    @staticmethod
    def _build_ancestry_map(sections):
        """
        Walk the course content tree (list of sections -> subsections -> units)
        and return {unit_id: {section_id, section_display_name, subsection_id,
        subsection_display_name}} so suggestions can carry full ancestry
        without trusting the LLM to know or repeat it correctly.
        """
        ancestry = {}
        for chapter in sections or []:
            section_id = chapter.get('location_id')
            section_name = chapter.get('display_name')
            for subsection in chapter.get('subsections', []) or []:
                subsection_id = subsection.get('location_id')
                subsection_name = subsection.get('display_name')
                for unit in subsection.get('units', []) or []:
                    unit_id = unit.get('location_id') or unit.get('unit_id')
                    if not unit_id:
                        continue
                    ancestry[unit_id] = {
                        'section_id': section_id,
                        'section_display_name': section_name,
                        'subsection_id': subsection_id,
                        'subsection_display_name': subsection_name,
                    }
        return ancestry

    @staticmethod
    def _known_location_ids(ancestry_map):
        """
        Every section/subsection/unit id in the course tree, gathered from
        ancestry_map. Lets the filter tell "this unit legitimately has zero
        suggestions" apart from "this location isn't part of the course tree
        at all" (e.g. the course's own root usage key on the outline page) —
        both would otherwise produce an empty match.
        """
        known = set()
        for unit_id, ancestry in ancestry_map.items():
            known.add(unit_id)
            if ancestry['section_id']:
                known.add(ancestry['section_id'])
            if ancestry['subsection_id']:
                known.add(ancestry['subsection_id'])
        return known

    @staticmethod
    def _sort_by_course_order(suggestions, ancestry_map):
        """
        Order suggestions by their unit's position in the course outline
        (ancestry_map's iteration order, itself built by walking the outline
        top to bottom) so cross-unit "next/previous suggestion" navigation
        follows the course structure instead of arbitrary LLM output order.
        """
        order = {unit_id: idx for idx, unit_id in enumerate(ancestry_map.keys())}
        return sorted(suggestions, key=lambda s: order.get(s.get('unit_id'), len(order)))

    @staticmethod
    def _filter_suggestions_for_location(suggestions, location_id, known_location_ids):
        """
        Return only suggestions belonging under location_id (matched against
        its unit, subsection, or section id). If location_id isn't part of
        the course tree at all, return everything instead — that's the
        course-outline case, not a "no suggestions here" case.
        """
        if not location_id or location_id not in known_location_ids:
            return suggestions
        return [
            s for s in suggestions
            if location_id in (s.get('unit_id'), s.get('section_id'), s.get('subsection_id'))
        ]

    def _resolve_extra_instructions(self, input_data, metadata):
        """
        Resolve which guidelines to use: an explicit non-empty value from
        this request, or the course's previously stored guidelines, so every
        author sees the same guidelines unless someone actively changes them.
        """
        provided = (input_data or {}).get('extra_instructions')
        if provided and provided.strip():
            return provided.strip()
        return metadata.get('extra_instructions', '')

    def run(self, input_data):
        """
        Fetch the whole course's content and ask the LLM for content
        improvement suggestions, then return the subset relevant to
        self.location_id.
        """

        openedx_processor = OpenEdXProcessor(
            processor_config=self.profile.processor_config,
            course_id=self.course_id,
            user=self.user,
        )
        content_result = openedx_processor.process()

        if content_result and 'error' in content_result:
            return {
                'error': content_result['error'],
                'status': 'OpenEdXProcessor error'
            }

        ancestry_map = self._build_ancestry_map(content_result.get('sections'))
        known_location_ids = self._known_location_ids(ancestry_map)

        llm_input_content = str(content_result)

        metadata = self.session.metadata or {}
        extra_instructions = self._resolve_extra_instructions(input_data, metadata)
        llm_input_data = dict(input_data or {})
        llm_input_data['extra_instructions'] = extra_instructions

        with open(self._schema_path, 'r', encoding='utf-8') as f:
            self.llm_processor = LLMProcessor(
                config=self.profile.processor_config,
                extra_params={"response_format": json.load(f)}
            )
        llm_result = self.llm_processor.process(context=llm_input_content, input_data=llm_input_data)

        if llm_result and 'error' in llm_result:
            return {
                'error': llm_result['error'],
                'status': 'LLMProcessor error'
            }

        response_payload = llm_result.get('response', {}) or {}
        suggestions = response_payload.get('suggestions', []) or []
        for suggestion in suggestions:
            suggestion['id'] = str(uuid.uuid4())
            suggestion.update(ancestry_map.get(suggestion.get('unit_id'), {
                'section_id': None,
                'section_display_name': None,
                'subsection_id': None,
                'subsection_display_name': None,
            }))
        suggestions = self._sort_by_course_order(suggestions, ancestry_map)

        metadata['suggestions'] = suggestions
        metadata['extra_instructions'] = extra_instructions
        metadata['known_location_ids'] = sorted(known_location_ids)
        self.session.metadata = metadata
        self.session.save(update_fields=["metadata"])

        self._emit_workflow_event(EVENT_NAME_WORKFLOW_COMPLETED)

        return {
            'status': 'completed',
            'response': {
                'suggestions': self._filter_suggestions_for_location(
                    suggestions, self.location_id, known_location_ids
                ),
                'course_suggestions': suggestions,
                'extra_instructions': extra_instructions,
            },
        }

    def get_current_session_response(self, _):
        """
        Retrieve the current session state, filtered to self.location_id.

        ``status`` distinguishes "never generated / cleared" (no_suggestions)
        from "generated at least once" (completed, though the filtered list
        may legitimately be empty for this location). Either way,
        extra_instructions is always returned so the request form can
        prefill the course's stored guidelines.
        """
        metadata = self.session.metadata or {}
        if "suggestions" in metadata:
            known_location_ids = set(metadata.get('known_location_ids', []))
            return {
                'response': {
                    'suggestions': self._filter_suggestions_for_location(
                        metadata['suggestions'], self.location_id, known_location_ids
                    ),
                    'course_suggestions': metadata['suggestions'],
                    'extra_instructions': metadata.get('extra_instructions', ''),
                },
                'status': 'completed',
            }
        return {
            'response': {
                'suggestions': [],
                'course_suggestions': [],
                'extra_instructions': metadata.get('extra_instructions', ''),
            },
            'status': 'no_suggestions',
        }

    def clear_session(self, _):
        """
        Clear generated suggestions but keep the session row (and its
        extra_instructions) alive, so the next author sees the same
        guidelines prefilled instead of starting from a blank field.
        """
        metadata = self.session.metadata or {}
        metadata.pop('suggestions', None)
        metadata.pop('known_location_ids', None)
        self.session.metadata = metadata
        self.session.save(update_fields=['metadata'])
        return {
            'response': '',
            'status': 'session_cleared',
        }
