"""
Tests for content_suggestions_orchestrator.
"""
# pylint: disable=protected-access

import json
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from opaque_keys.edx.keys import CourseKey

from openedx_ai_extensions.workflows.models import AIWorkflowProfile, AIWorkflowScope, AIWorkflowSession
from openedx_ai_extensions.workflows.orchestrators.content_suggestions_orchestrator import (
    ContentSuggestionsOrchestrator,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user(db):  # pylint: disable=unused-argument
    return User.objects.create_user(
        username="content_suggestions_test_user",
        email="content_suggestions@example.com",
        password="password123",
    )


@pytest.fixture
def course_key():
    return CourseKey.from_string("course-v1:edX+DemoX+Demo_Course")


@pytest.fixture
def workflow_profile(db):  # pylint: disable=unused-argument
    return AIWorkflowProfile.objects.create(
        slug="test-content-suggestions",
        description="Content suggestions profile for tests",
        base_filepath="experimental/content_suggestions.json",
        content_patch="{}",
    )


@pytest.fixture
def workflow_scope(workflow_profile, course_key):  # pylint: disable=redefined-outer-name
    return AIWorkflowScope.objects.create(
        location_regex=".*",
        course_id=course_key,
        service_variant="cms",
        profile=workflow_profile,
        enabled=True,
    )


UNIT_1 = "block-v1:edX+DemoX+Demo_Course+type@vertical+block@unit1"
UNIT_2 = "block-v1:edX+DemoX+Demo_Course+type@vertical+block@unit2"
SECTION_1 = "block-v1:edX+DemoX+Demo_Course+type@chapter+block@sec1"
SUBSECTION_1 = "block-v1:edX+DemoX+Demo_Course+type@sequential+block@sub1"


def build_outline():
    return [
        {
            "location_id": SECTION_1,
            "display_name": "Week 1",
            "subsections": [
                {
                    "location_id": SUBSECTION_1,
                    "display_name": "Getting Started",
                    "units": [
                        {"location_id": UNIT_1, "display_name": "Introduction"},
                        {"location_id": UNIT_2, "display_name": "Deep Dive"},
                    ],
                },
            ],
        },
    ]


def make_orchestrator(workflow_scope, user, course_key, location_id=None):  # pylint: disable=redefined-outer-name
    """Build a ContentSuggestionsOrchestrator for the given scope/location."""
    context = {
        "course_id": str(course_key),
        "location_id": location_id,
    }
    return ContentSuggestionsOrchestrator(
        workflow=workflow_scope,
        user=user,
        context=context,
    )


@pytest.fixture
def orchestrator(workflow_scope, user, course_key):  # pylint: disable=redefined-outer-name
    return make_orchestrator(workflow_scope, user, course_key)


# ===========================================================================
# _build_ancestry_map / _known_location_ids
# ===========================================================================


def test_build_ancestry_map_maps_units_to_ancestry():
    ancestry = ContentSuggestionsOrchestrator._build_ancestry_map(build_outline())

    assert ancestry[UNIT_1] == {
        "section_id": SECTION_1,
        "section_display_name": "Week 1",
        "subsection_id": SUBSECTION_1,
        "subsection_display_name": "Getting Started",
    }
    assert ancestry[UNIT_2]["section_id"] == SECTION_1


def test_build_ancestry_map_skips_units_without_location_id():
    outline = [
        {
            "location_id": SECTION_1,
            "display_name": "Week 1",
            "subsections": [
                {
                    "location_id": SUBSECTION_1,
                    "display_name": "Getting Started",
                    "units": [{"display_name": "No location"}],
                },
            ],
        },
    ]
    ancestry = ContentSuggestionsOrchestrator._build_ancestry_map(outline)
    assert not ancestry


def test_build_ancestry_map_empty_outline():
    assert not ContentSuggestionsOrchestrator._build_ancestry_map([])
    assert not ContentSuggestionsOrchestrator._build_ancestry_map(None)


def test_known_location_ids_includes_all_tree_levels():
    ancestry = ContentSuggestionsOrchestrator._build_ancestry_map(build_outline())
    known = ContentSuggestionsOrchestrator._known_location_ids(ancestry)

    assert known == {UNIT_1, UNIT_2, SECTION_1, SUBSECTION_1}


# ===========================================================================
# _sort_by_course_order
# ===========================================================================


def test_sort_by_course_order_orders_by_outline_position():
    ancestry = ContentSuggestionsOrchestrator._build_ancestry_map(build_outline())
    suggestions = [
        {"id": "s1", "unit_id": UNIT_2},
        {"id": "s2", "unit_id": UNIT_1},
    ]

    sorted_suggestions = ContentSuggestionsOrchestrator._sort_by_course_order(suggestions, ancestry)

    assert [s["id"] for s in sorted_suggestions] == ["s2", "s1"]


def test_sort_by_course_order_unknown_unit_goes_last():
    ancestry = ContentSuggestionsOrchestrator._build_ancestry_map(build_outline())
    suggestions = [
        {"id": "unknown", "unit_id": "not-in-outline"},
        {"id": "s2", "unit_id": UNIT_1},
    ]

    sorted_suggestions = ContentSuggestionsOrchestrator._sort_by_course_order(suggestions, ancestry)

    assert [s["id"] for s in sorted_suggestions] == ["s2", "unknown"]


# ===========================================================================
# _filter_suggestions_for_location
# ===========================================================================


def test_filter_suggestions_no_location_returns_everything():
    suggestions = [{"unit_id": UNIT_1}, {"unit_id": UNIT_2}]
    result = ContentSuggestionsOrchestrator._filter_suggestions_for_location(suggestions, None, {UNIT_1, UNIT_2})
    assert result == suggestions


def test_filter_suggestions_location_outside_tree_returns_everything():
    suggestions = [{"unit_id": UNIT_1}, {"unit_id": UNIT_2}]
    result = ContentSuggestionsOrchestrator._filter_suggestions_for_location(
        suggestions, "course-v1:edX+DemoX+Demo_Course", {UNIT_1, UNIT_2}
    )
    assert result == suggestions


def test_filter_suggestions_unit_location_matches_only_its_unit():
    suggestions = [
        {"unit_id": UNIT_1, "section_id": SECTION_1, "subsection_id": SUBSECTION_1},
        {"unit_id": UNIT_2, "section_id": SECTION_1, "subsection_id": SUBSECTION_1},
    ]
    known = {UNIT_1, UNIT_2, SECTION_1, SUBSECTION_1}

    result = ContentSuggestionsOrchestrator._filter_suggestions_for_location(suggestions, UNIT_1, known)

    assert len(result) == 1
    assert result[0]["unit_id"] == UNIT_1


def test_filter_suggestions_real_unit_with_zero_suggestions_returns_empty():
    """A known unit with no suggestions must return [] and NOT fall back to everything."""
    suggestions = [{"unit_id": UNIT_2, "section_id": SECTION_1, "subsection_id": SUBSECTION_1}]
    known = {UNIT_1, UNIT_2, SECTION_1, SUBSECTION_1}

    result = ContentSuggestionsOrchestrator._filter_suggestions_for_location(suggestions, UNIT_1, known)

    assert result == []


def test_filter_suggestions_section_location_matches_all_its_descendants():
    suggestions = [
        {"unit_id": UNIT_1, "section_id": SECTION_1, "subsection_id": SUBSECTION_1},
        {"unit_id": UNIT_2, "section_id": SECTION_1, "subsection_id": SUBSECTION_1},
    ]
    known = {UNIT_1, UNIT_2, SECTION_1, SUBSECTION_1}

    result = ContentSuggestionsOrchestrator._filter_suggestions_for_location(suggestions, SECTION_1, known)

    assert len(result) == 2


# ===========================================================================
# _resolve_extra_instructions
# ===========================================================================


def test_resolve_extra_instructions_prefers_explicit_value(orchestrator):  # pylint: disable=redefined-outer-name
    result = orchestrator._resolve_extra_instructions(
        {"extra_instructions": "Use third person."}, {"extra_instructions": "stored"}
    )
    assert result == "Use third person."


def test_resolve_extra_instructions_falls_back_to_stored_value(orchestrator):  # pylint: disable=redefined-outer-name
    result = orchestrator._resolve_extra_instructions(
        {"extra_instructions": "   "}, {"extra_instructions": "stored"}
    )
    assert result == "stored"


def test_resolve_extra_instructions_no_input_data_falls_back_to_stored(
    orchestrator,  # pylint: disable=redefined-outer-name
):
    result = orchestrator._resolve_extra_instructions(None, {"extra_instructions": "stored"})
    assert result == "stored"


def test_resolve_extra_instructions_defaults_to_empty_string(orchestrator):  # pylint: disable=redefined-outer-name
    result = orchestrator._resolve_extra_instructions({}, {})
    assert result == ""


# ===========================================================================
# run() — error paths
# ===========================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.content_suggestions_orchestrator.OpenEdXProcessor")
def test_run_openedx_error(mock_openedx_class, orchestrator):  # pylint: disable=redefined-outer-name
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"error": "Course not found"}
    mock_openedx_class.return_value = mock_openedx

    result = orchestrator.run({})

    assert result == {"error": "Course not found", "status": "OpenEdXProcessor error"}


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.content_suggestions_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.content_suggestions_orchestrator.LLMProcessor")
def test_run_llm_error(mock_llm_class, mock_openedx_class, orchestrator):  # pylint: disable=redefined-outer-name
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"outline": json.dumps(build_outline())}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {"error": "AI API failed"}
    mock_llm_class.return_value = mock_llm

    result = orchestrator.run({})

    assert result == {"error": "AI API failed", "status": "LLMProcessor error"}


# ===========================================================================
# run() — success path
# ===========================================================================


def _mock_llm_success(mock_llm_class, suggestions):
    mock_llm = Mock()
    mock_llm.process.return_value = {"response": {"suggestions": suggestions}}
    mock_llm_class.return_value = mock_llm
    return mock_llm


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.content_suggestions_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.content_suggestions_orchestrator.LLMProcessor")
def test_run_success_enriches_and_persists_suggestions(
    mock_llm_class, mock_openedx_class, orchestrator,  # pylint: disable=redefined-outer-name
):
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"outline": json.dumps(build_outline())}
    mock_openedx_class.return_value = mock_openedx

    raw_suggestions = [
        {"unit_id": UNIT_2, "title": "Second"},
        {"unit_id": UNIT_1, "title": "First"},
    ]
    _mock_llm_success(mock_llm_class, raw_suggestions)

    with patch.object(orchestrator, "_emit_workflow_event") as mock_emit:
        result = orchestrator.run({"extra_instructions": "Be concise."})

    assert result["status"] == "completed"
    course_suggestions = result["response"]["course_suggestions"]
    # sorted by course order: unit1 before unit2
    assert [s["title"] for s in course_suggestions] == ["First", "Second"]
    for suggestion in course_suggestions:
        assert "id" in suggestion
        assert suggestion["section_id"] == SECTION_1
        assert suggestion["subsection_id"] == SUBSECTION_1
    assert result["response"]["extra_instructions"] == "Be concise."
    mock_emit.assert_called_once()

    orchestrator.session.refresh_from_db()
    assert orchestrator.session.metadata["extra_instructions"] == "Be concise."
    assert set(orchestrator.session.metadata["known_location_ids"]) == {UNIT_1, UNIT_2, SECTION_1, SUBSECTION_1}
    assert len(orchestrator.session.metadata["suggestions"]) == 2


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.content_suggestions_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.content_suggestions_orchestrator.LLMProcessor")
def test_run_filters_response_to_current_unit_location(
    mock_llm_class, mock_openedx_class, workflow_scope, user, course_key,  # pylint: disable=redefined-outer-name
):
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"outline": json.dumps(build_outline())}
    mock_openedx_class.return_value = mock_openedx

    raw_suggestions = [
        {"unit_id": UNIT_1, "title": "First"},
        {"unit_id": UNIT_2, "title": "Second"},
    ]
    _mock_llm_success(mock_llm_class, raw_suggestions)

    unit_orchestrator = make_orchestrator(workflow_scope, user, course_key, location_id=UNIT_1)
    with patch.object(unit_orchestrator, "_emit_workflow_event"):
        result = unit_orchestrator.run({})

    filtered_titles = [s["title"] for s in result["response"]["suggestions"]]
    assert filtered_titles == ["First"]
    # course_suggestions stays unfiltered
    assert len(result["response"]["course_suggestions"]) == 2


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.content_suggestions_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.content_suggestions_orchestrator.LLMProcessor")
def test_run_no_suggestions_key_defaults_to_empty_list(
    mock_llm_class, mock_openedx_class, orchestrator,  # pylint: disable=redefined-outer-name
):
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"outline": json.dumps(build_outline())}
    mock_openedx_class.return_value = mock_openedx

    mock_llm = Mock()
    mock_llm.process.return_value = {"response": {}}
    mock_llm_class.return_value = mock_llm

    with patch.object(orchestrator, "_emit_workflow_event"):
        result = orchestrator.run({})

    assert result["status"] == "completed"
    assert result["response"]["suggestions"] == []
    assert result["response"]["course_suggestions"] == []


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.content_suggestions_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.content_suggestions_orchestrator.LLMProcessor")
def test_run_passes_json_schema_as_response_format(
    mock_llm_class, mock_openedx_class, orchestrator,  # pylint: disable=redefined-outer-name
):
    mock_openedx = Mock()
    mock_openedx.process.return_value = {"outline": json.dumps(build_outline())}
    mock_openedx_class.return_value = mock_openedx

    _mock_llm_success(mock_llm_class, [])

    with patch.object(orchestrator, "_emit_workflow_event"):
        orchestrator.run({})

    call_kwargs = mock_llm_class.call_args[1]
    assert "response_format" in call_kwargs["extra_params"]


@pytest.mark.django_db
@patch("openedx_ai_extensions.workflows.orchestrators.content_suggestions_orchestrator.OpenEdXProcessor")
@patch("openedx_ai_extensions.workflows.orchestrators.content_suggestions_orchestrator.LLMProcessor")
def test_run_reuses_stored_extra_instructions_when_not_provided(
    mock_llm_class, mock_openedx_class, orchestrator,  # pylint: disable=redefined-outer-name
):
    orchestrator.session.metadata = {"extra_instructions": "Previously stored guidelines."}
    orchestrator.session.save(update_fields=["metadata"])

    mock_openedx = Mock()
    mock_openedx.process.return_value = {"outline": json.dumps(build_outline())}
    mock_openedx_class.return_value = mock_openedx

    _mock_llm_success(mock_llm_class, [])

    with patch.object(orchestrator, "_emit_workflow_event"):
        result = orchestrator.run({})

    assert result["response"]["extra_instructions"] == "Previously stored guidelines."


# ===========================================================================
# get_current_session_response
# ===========================================================================


@pytest.mark.django_db
def test_get_current_session_response_with_suggestions(orchestrator):  # pylint: disable=redefined-outer-name
    suggestions = [
        {"id": "s1", "unit_id": UNIT_1},
        {"id": "s2", "unit_id": UNIT_2},
    ]
    orchestrator.session.metadata = {
        "suggestions": suggestions,
        "known_location_ids": [UNIT_1, UNIT_2],
        "extra_instructions": "Be concise.",
    }
    orchestrator.session.save(update_fields=["metadata"])

    result = orchestrator.get_current_session_response(None)

    assert result["status"] == "completed"
    assert result["response"]["suggestions"] == suggestions
    assert result["response"]["course_suggestions"] == suggestions
    assert result["response"]["extra_instructions"] == "Be concise."


@pytest.mark.django_db
def test_get_current_session_response_filters_by_location(
    workflow_scope, user, course_key,  # pylint: disable=redefined-outer-name
):
    unit_orchestrator = make_orchestrator(workflow_scope, user, course_key, location_id=UNIT_1)
    unit_orchestrator.session.metadata = {
        "suggestions": [{"id": "s1", "unit_id": UNIT_1}, {"id": "s2", "unit_id": UNIT_2}],
        "known_location_ids": [UNIT_1, UNIT_2],
        "extra_instructions": "",
    }
    unit_orchestrator.session.save(update_fields=["metadata"])

    result = unit_orchestrator.get_current_session_response(None)

    assert [s["id"] for s in result["response"]["suggestions"]] == ["s1"]
    assert result["response"]["course_suggestions"] == unit_orchestrator.session.metadata["suggestions"]


@pytest.mark.django_db
def test_get_current_session_response_no_suggestions_yet(orchestrator):  # pylint: disable=redefined-outer-name
    orchestrator.session.metadata = {"extra_instructions": "kept guidelines"}
    orchestrator.session.save(update_fields=["metadata"])

    result = orchestrator.get_current_session_response(None)

    assert result == {
        "response": {
            "suggestions": [],
            "course_suggestions": [],
            "extra_instructions": "kept guidelines",
        },
        "status": "no_suggestions",
    }


@pytest.mark.django_db
def test_get_current_session_response_empty_metadata(orchestrator):  # pylint: disable=redefined-outer-name
    orchestrator.session.metadata = {}
    orchestrator.session.save(update_fields=["metadata"])

    result = orchestrator.get_current_session_response(None)

    assert result["status"] == "no_suggestions"
    assert result["response"]["extra_instructions"] == ""


# ===========================================================================
# clear_session
# ===========================================================================


@pytest.mark.django_db
def test_clear_session_removes_suggestions_but_keeps_extra_instructions(
    orchestrator,  # pylint: disable=redefined-outer-name
):
    orchestrator.session.metadata = {
        "suggestions": [{"id": "s1"}],
        "known_location_ids": [UNIT_1],
        "extra_instructions": "keep me",
    }
    orchestrator.session.save(update_fields=["metadata"])
    session_id = orchestrator.session.id

    result = orchestrator.clear_session(None)

    assert result == {"response": "", "status": "session_cleared"}

    orchestrator.session.refresh_from_db()
    # The session row itself survives clear_session (unlike the base class,
    # which deletes it) so extra_instructions stays available for prefill.
    assert orchestrator.session.id == session_id
    assert "suggestions" not in orchestrator.session.metadata
    assert "known_location_ids" not in orchestrator.session.metadata
    assert orchestrator.session.metadata["extra_instructions"] == "keep me"


@pytest.mark.django_db
def test_clear_session_with_empty_metadata_does_not_raise(orchestrator):  # pylint: disable=redefined-outer-name
    # A freshly created session already has empty metadata ({}) — the
    # `metadata` column is NOT NULL, so None is never a valid stored value.
    orchestrator.session.metadata = {}
    orchestrator.session.save(update_fields=["metadata"])

    result = orchestrator.clear_session(None)

    assert result == {"response": "", "status": "session_cleared"}


# ===========================================================================
# _schema_path
# ===========================================================================


def test_schema_path_points_to_content_suggestions_json(orchestrator):  # pylint: disable=redefined-outer-name
    schema_path = orchestrator._schema_path
    assert schema_path.name == "content_suggestions.json"
    assert "response_schemas" in str(schema_path)


# ===========================================================================
# CrossSlotSessionOrchestrator sharing behavior (via ContentSuggestionsOrchestrator)
# ===========================================================================


@pytest.mark.django_db
def test_session_is_shared_across_scopes_for_same_profile(
    workflow_profile, course_key, user,  # pylint: disable=redefined-outer-name
):
    scope_a = AIWorkflowScope.objects.create(
        location_regex=".*",
        course_id=course_key,
        service_variant="cms",
        profile=workflow_profile,
        ui_slot_selector_id="sidebar1",
        enabled=True,
    )
    scope_b = AIWorkflowScope.objects.create(
        location_regex=".*",
        course_id=course_key,
        service_variant="cms",
        profile=workflow_profile,
        ui_slot_selector_id="educator-1",
        enabled=True,
    )

    orchestrator_a = make_orchestrator(scope_a, user, course_key)
    orchestrator_a.session.metadata = {"suggestions": [{"id": "s1", "unit_id": UNIT_1}]}
    orchestrator_a.session.save(update_fields=["metadata"])

    orchestrator_b = make_orchestrator(scope_b, user, course_key)

    assert orchestrator_b.session.id == orchestrator_a.session.id
    assert orchestrator_b.session.metadata["suggestions"][0]["id"] == "s1"


@pytest.mark.django_db
def test_session_has_no_location_id(orchestrator):  # pylint: disable=redefined-outer-name
    assert orchestrator.session.location_id is None


@pytest.mark.django_db
def test_session_tolerates_pre_existing_duplicate_scope_rows(
    workflow_profile, course_key, user,  # pylint: disable=redefined-outer-name
):
    """
    If two scope-keyed session rows already exist for this (user, profile,
    course_id) from before CrossSlotSessionOrchestrator existed, instantiating
    it must not raise MultipleObjectsReturned — it should deterministically
    pick one (the earliest created).
    """
    scope_a = AIWorkflowScope.objects.create(
        location_regex=".*",
        course_id=course_key,
        service_variant="cms",
        profile=workflow_profile,
        ui_slot_selector_id="sidebar1",
        enabled=True,
    )
    scope_b = AIWorkflowScope.objects.create(
        location_regex=".*",
        course_id=course_key,
        service_variant="cms",
        profile=workflow_profile,
        ui_slot_selector_id="educator-1",
        enabled=True,
    )

    first = AIWorkflowSession.objects.create(
        user=user, scope=scope_a, profile=workflow_profile, course_id=course_key,
    )
    AIWorkflowSession.objects.create(
        user=user, scope=scope_b, profile=workflow_profile, course_id=course_key,
    )

    later_orchestrator = make_orchestrator(scope_b, user, course_key)

    assert later_orchestrator.session.id == first.id
