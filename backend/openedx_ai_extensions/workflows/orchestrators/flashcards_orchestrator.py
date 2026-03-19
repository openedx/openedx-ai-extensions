"""
Orchestrators for handling different AI workflow patterns in Open edX.
"""
import json
import logging
from pathlib import Path

from openedx_ai_extensions.processors import (
    LLMProcessor,
    OpenEdXProcessor,
)
from openedx_ai_extensions.xapi.constants import EVENT_NAME_WORKFLOW_COMPLETED

from .session_based_orchestrator import SessionBasedOrchestrator

logger = logging.getLogger(__name__)


class FlashCardsOrchestrator(SessionBasedOrchestrator):
    """
    Orchestrator for flashcards generation using LLM.
    Does a single call to an LLM and gives a response.
    """

    @property
    def _schema_path(self):
        return (
            Path(__file__).resolve().parent.parent.parent
            / "response_schemas"
            / "flashcards.json"
        )

    def run(self, input_data):
        """
        Executes the content fetching, LLM processing, and handles streaming
        or structured response return.
        """

        # --- 1. Process with OpenEdX processor (Content Fetching) ---
        openedx_processor = OpenEdXProcessor(
            processor_config=self.profile.processor_config,
            location_id=self.location_id,
            course_id=self.course_id,
            user=self.user,
        )
        content_result = openedx_processor.process()

        # Early return on error during content fetching
        if content_result and 'error' in content_result:
            return {
                'error': content_result['error'],
                'status': 'OpenEdXProcessor error'
            }

        # Convert fetched content to a string format suitable for the LLM
        llm_input_content = str(content_result)

        # --- 2. Process with LLM processor ---
        with open(self._schema_path, 'r', encoding='utf-8') as f:
            llm_processor = LLMProcessor(
                config=self.profile.processor_config,
                extra_params={"response_format": json.load(f)}
            )
        if input_data.get('num_cards', None) is None:
            # Generate random number of cards between 1 and 25 if num_cards is not provided or is None
            input_data['num_cards'] = 0

        llm_result = llm_processor.process(
            context=llm_input_content,
            input_data=input_data,
        )

        # --- 5. Handle LLM Error (Non-Streaming) ---
        if llm_result and 'error' in llm_result:
            # Early return on error during non-streaming LLM processing
            return {
                'error': llm_result['error'],
                'status': 'LLMProcessor error'
            }

        # 6. Emit completed event for one-shot workflow
        self._emit_workflow_event(EVENT_NAME_WORKFLOW_COMPLETED)

        # Extract cards from the LLM response, which may be either:
        # - a dict containing a "cards" list, or
        # - a list of card dicts directly.
        response_obj = llm_result.get('response')
        cards = []
        if isinstance(response_obj, dict):
            potential_cards = response_obj.get('cards')
            if isinstance(potential_cards, list):
                cards = potential_cards
        elif isinstance(response_obj, list):
            cards = response_obj

        if cards is not None:
            for card in cards:
                # Ensure each card has the scheduling metadata required by the client.
                if isinstance(card, dict):
                    card['nextReviewTime'] = 0
                    card['interval'] = 1
                    card['easeFactor'] = 2.5
                    card['repetitions'] = 0
                    card['lastReviewedAt'] = None

        # Reconstruct the response in the same structural shape we received.
        if isinstance(response_obj, dict):
            enriched_response = dict(response_obj)
            enriched_response['cards'] = cards
        else:
            enriched_response = cards

        # --- 7. Return Structured Non-Streaming Result ---
        # If execution reaches this point, we have a successful, non-streaming result (Dict).
        response_data = {
            'response': enriched_response,
            'status': 'completed',
            'metadata': {
                'tokens_used': llm_result.get('tokens_used'),
                'model_used': llm_result.get('model_used')
            }
        }
        return response_data

    def save(self, input_data):
        """
        Saves the generated flashcards to the database or a file.
        This is a placeholder implementation and should be replaced with actual saving logic.
        """
        # Placeholder: Implement actual saving logic here (e.g., save to DB or file)
        self.session.metadata['cards'] = input_data.get('card_stack')
        self.session.save(update_fields=['metadata'])
        return {
            'status': 'flashcards_saved',
            'saved_data': input_data
        }
