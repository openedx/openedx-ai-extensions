"""
Orchestrators for handling different AI workflow patterns in Open edX.
"""
import json
import random
from pathlib import Path

from openedx_ai_extensions.processors import LLMProcessor, OpenEdXProcessor
from openedx_ai_extensions.xapi.constants import EVENT_NAME_WORKFLOW_COMPLETED

from .session_based_orchestrator import ScopedSessionOrchestrator


class FlashCardsOrchestrator(ScopedSessionOrchestrator):
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

    def _get_structured_cards(self, cards):
        """
        Helper method to structure cards in a consistent format.
        """
        if isinstance(cards, dict):
            cards = cards.get('cards', [])
        if not isinstance(cards, list):
            cards = []

        for card in cards:
            if isinstance(card, dict):
                card['nextReviewTime'] = 0
                card['interval'] = 1
                card['easeFactor'] = 2.5
                card['repetitions'] = 0
                card['lastReviewedAt'] = None

        return cards

    def run(self, input_data):
        """
        Executes the content fetching, LLM processing, and handles streaming
        or structured response return.
        """

        # --- 1. Process with OpenEdX processor (Content Fetching) ---
        self._set_status_message("Fetching unit content...")
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

        if input_data.get('num_cards', None) is None:
            # Generate random number of cards between 1 and 25 if num_cards is not provided or is None
            input_data['num_cards'] = random.randint(1, 25)

        metadata = self.session.metadata or {}
        existing_cards = metadata.get('cards')
        if isinstance(existing_cards, list):
            existing_cards_str = ""
            for card in existing_cards:
                if isinstance(card, dict) and card.get('question') and card.get('answer'):
                    card_id = card.get('id', 'N/A')
                    question = card['question']
                    answer = card['answer']
                    existing_cards_str += (
                        f"Id: {card_id}\nQuestion: {question}"
                        f"\nAnswer: {answer}\n\n"
                    )
            input_data['existing_cards'] = existing_cards_str

        with open(self._schema_path, 'r', encoding='utf-8') as f:
            self.llm_processor = LLMProcessor(
                config=self.profile.processor_config,
                extra_params={"response_format": json.load(f)}
            )
        self._set_status_message("Generating flashcards with LLM...")
        llm_result = self.llm_processor.process(
            context=llm_input_content,
            input_data=input_data,
        )

        if llm_result and 'error' in llm_result:
            return {
                'error': llm_result['error'],
                'status': 'LLMProcessor error'
            }

        self._emit_workflow_event(EVENT_NAME_WORKFLOW_COMPLETED)

        response_obj = llm_result.get('response')
        cards = self._get_structured_cards(response_obj)

        existing_cards = self.session.metadata.get('cards')
        if isinstance(existing_cards, list):
            existing_cards.extend(cards)
        else:
            self.session.metadata['cards'] = cards
        self.session.save(update_fields=['metadata'])

        response_data = {
            'response': cards,
            'status': 'completed',
        }
        return response_data

    def save(self, input_data):
        """
        Saves the generated flashcards to the database or a file.
        This is a placeholder implementation and should be replaced with actual saving logic.
        """
        cards = input_data.get('cards')
        if cards is None:
            card_stack = input_data.get('card_stack')
            if isinstance(card_stack, dict):
                cards = card_stack.get('cards')
            else:
                cards = card_stack
        self.session.metadata['cards'] = cards
        self.session.save(update_fields=['metadata'])
        num_cards = len(cards) if cards else 0
        return {
            'status': 'saved',
            'message': f'{num_cards} cards saved successfully.'
        }

    def get_current_session_response(self, _):
        """
        Retrieve the current session state.

        - If flashcards were generated but not yet saved: return them for review.
        - Otherwise: return None.
        """
        metadata = self.session.metadata or {}
        if "cards" in metadata:
            return {
                'cards': metadata['cards'],
                'status': 'completed',
            }
        return {
            'cards': None,
            'status': 'no_flashcards',
        }
