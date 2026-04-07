"""
Tests for EducatorAssistantProcessor — generate_quiz_questions and refine_quiz_question.
"""
import json
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model

from openedx_ai_extensions.processors.llm.educator_assistant_processor import EducatorAssistantProcessor

User = get_user_model()


@pytest.fixture
def user(db):  # pylint: disable=unused-argument
    """Create and return a test user."""
    return User.objects.create_user(
        username="educator_proc_user",
        email="proc@example.com",
        password="password123",
    )


@pytest.fixture
def processor_config():
    return {
        "EducatorAssistantProcessor": {
            "function": "generate_quiz_questions",
            "provider": "default",
        },
    }


@pytest.fixture
def ai_settings(settings):
    """Configure AI_EXTENSIONS settings for tests."""
    settings.AI_EXTENSIONS = {
        "default": {
            "MODEL": "openai/gpt-4",
            "API_KEY": "test-key",
        }
    }
    return settings


@pytest.fixture
def processor(processor_config, user, ai_settings):  # pylint: disable=redefined-outer-name,unused-argument
    """Create an EducatorAssistantProcessor instance."""
    return EducatorAssistantProcessor(
        config=processor_config,
        user=user,
        context="Course unit content about Python programming.",
    )


# ===========================================================================
# EducatorAssistantProcessor.refine_quiz_question
# ===========================================================================


@pytest.mark.django_db
def test_refine_quiz_question_success(processor):  # pylint: disable=redefined-outer-name
    """
    refine_quiz_question loads the prompt, substitutes placeholders,
    calls the LLM, and returns a parsed response.
    """
    llm_response = json.dumps({
        "collection_name": "Python Quiz",
        "problems": [
            {
                "display_name": "Improved Q1",
                "question_html": "What does `len()` return?",
                "problem_type": "multiplechoiceresponse",
                "choices": [
                    {"text": "The length", "is_correct": True, "feedback": "Correct!"},
                    {"text": "The type", "is_correct": False, "feedback": "Wrong."},
                ],
                "answer_value": "",
                "tolerance": "",
                "explanation": "len() returns the number of items.",
                "demand_hints": [],
            }
        ],
    })

    mock_completion_result = {
        "response": llm_response,
        "model_used": "openai/gpt-4",
        "status": "success",
    }

    input_data = {
        "question_index": 0,
        "existing_question": {"display_name": "Q1", "problem_type": "multiplechoiceresponse"},
        "extra_instructions": "Make the question clearer.",
    }

    with patch.object(processor, "_call_completion_api", return_value=mock_completion_result):
        result = processor.refine_quiz_question(input_data=input_data)

    assert "error" not in result
    assert result["response"]["problems"][0]["display_name"] == "Improved Q1"


@pytest.mark.django_db
def test_refine_quiz_question_substitutes_placeholders(processor):  # pylint: disable=redefined-outer-name
    """
    refine_quiz_question replaces {{EXISTING_QUESTION}}, {{EXTRA_INSTRUCTIONS}},
    and {{CONTEXT}} placeholders in the prompt before calling the LLM.
    """
    llm_response = json.dumps({
        "collection_name": "Quiz",
        "problems": [{"display_name": "Refined"}],
    })

    captured_prompts = []

    def fake_call(prompt):
        captured_prompts.append(prompt)
        return {
            "response": llm_response,
        }

    input_data = {
        "question_index": 0,
        "existing_question": "ORIGINAL_QUESTION_TEXT",
        "extra_instructions": "Make it harder",
    }

    with patch.object(processor, "_call_completion_api", side_effect=fake_call):
        processor.refine_quiz_question(input_data=input_data)

    assert len(captured_prompts) == 1
    prompt = captured_prompts[0]
    # The placeholders should have been replaced with actual values
    assert "ORIGINAL_QUESTION_TEXT" in prompt
    assert "Make it harder" in prompt
    assert "Course unit content about Python programming." in prompt


# ===========================================================================
# EducatorAssistantProcessor.generate_quiz_questions
# ===========================================================================


@pytest.mark.django_db
def test_generate_quiz_questions_success(processor):  # pylint: disable=redefined-outer-name
    """
    generate_quiz_questions loads the prompt, calls the LLM,
    and returns parsed JSON response.
    """
    llm_response = json.dumps({
        "collection_name": "Python Basics",
        "problems": [
            {
                "display_name": "Q1",
                "question_html": "What is Python?",
                "problem_type": "multiplechoiceresponse",
                "choices": [
                    {"text": "A language", "is_correct": True, "feedback": ""},
                ],
                "answer_value": "",
                "tolerance": "",
                "explanation": "Python is a programming language.",
                "demand_hints": [],
            }
        ],
    })

    mock_result = {
        "response": llm_response,
        "status": "success",
    }

    with patch.object(processor, "_call_completion_api", return_value=mock_result):
        result = processor.generate_quiz_questions(input_data={"num_questions": 1})

    assert "error" not in result
    assert result["response"]["collection_name"] == "Python Basics"
    assert len(result["response"]["problems"]) == 1
