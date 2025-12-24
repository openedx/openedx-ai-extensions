"""
Database models for openedx_ai_extensions.
"""
import logging
import re
from uuid import uuid4

from django.db import models

logger = logging.getLogger(__name__)


class PromptTemplate(models.Model):
    """
    Reusable prompt templates for AI workflows.

    This is the source for reusable prompt text. Profiles can reference
    templates by slug (human-readable) or UUID (stable).

    Examples:
        - slug: "eli5", "summarize_unit", "explain_concept"
        - body: "You are a helpful AI that explains things simply..."

    .. no_pii:
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid4,
        editable=False,
        help_text="Stable UUID for referencing this template"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Human-readable identifier (e.g., 'eli5', 'summarize_unit')"
    )
    body = models.TextField(
        help_text="The prompt template text"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Model metadata."""

        ordering = ['slug']

    def __str__(self):
        """Return string representation."""
        return f"{self.slug}"

    def __repr__(self):
        """Return detailed string representation."""
        return f"<PromptTemplate: {self.slug}>"

    @classmethod
    def load_prompt(cls, template_identifier):
        """
        Load prompt text by slug or UUID.

        Uses regex to detect UUID format and query accordingly for efficiency.

        Args:
            template_identifier: Either a slug (str) or UUID string

        Returns:
            str or None: The prompt body, or None if not found
        """
        if not template_identifier:
            return None

        # UUID pattern: 32 hex digits with or without dashes
        uuid_pattern = re.compile(
            r'^[a-f\d]{8}-?([a-f\d]{4}-?){3}[a-f\d]{12}$',
            re.IGNORECASE
        )
        if uuid_pattern.match(str(template_identifier)):
            try:
                template = cls.objects.get(id=template_identifier)
                logger.info(f"Loaded prompt template by UUID: {template_identifier}")
                return template.body
            except cls.DoesNotExist:
                logger.warning(f"PromptTemplate with UUID '{template_identifier}' not found")
                return None
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"Error loading PromptTemplate by UUID '{template_identifier}': {e}")
                return None

        # Otherwise, try as slug
        try:
            template = cls.objects.get(slug=template_identifier)
            logger.info(f"Loaded prompt template by slug: {template_identifier}")
            return template.body
        except cls.DoesNotExist:
            logger.warning(f"PromptTemplate with slug '{template_identifier}' not found")
            return None
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"Error loading PromptTemplate by slug '{template_identifier}': {e}")
            return None
