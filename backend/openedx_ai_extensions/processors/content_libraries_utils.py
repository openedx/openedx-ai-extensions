"""
Utility functions and classes for content library operations.
"""
import logging
from uuid import uuid4

from django.db import transaction
from opaque_keys.edx.locator import LibraryLocatorV2
from openedx.core.djangoapps.content_libraries import api, permissions  # pylint: disable=import-error
from openedx.core.djangoapps.content_libraries.rest_api import serializers  # pylint: disable=import-error

logger = logging.getLogger(__name__)


class ContentLibraryHelper:
    """
    Helper class for content library operations
    """

    def __init__(self, library_key: str, user) -> None:
        self.library_key = LibraryLocatorV2.from_string(library_key)
        self.user = user

    def create_collection_and_add_items(self, items, title, description="") -> str:
        """Create a collection and add items to it."""
        with transaction.atomic():
            collection = self.create_collection(title=title, description=description)

            opaque_keys = []
            for problem_info in items:

                block_data = {
                  "block_type": problem_info['category'],
                  "definition_id": str(uuid4()),
                  "can_stand_alone": True,
                }

                problem = self.create_block(block_data)
                self.modify_block_olx(usage_key=problem.usage_key, data=problem_info['data'])

                opaque_keys.append(problem.usage_key)

            self.update_library_collection_items(
                collection_key=collection.key,
                item_keys=opaque_keys
            )
        return str(collection.key)

    def create_block(self, data):
        """Create a library block."""
        serializer = serializers.LibraryXBlockCreationSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        try:
            result = api.create_library_block(self.library_key, user_id=self.user.id, **serializer.validated_data)
        except api.IncompatibleTypesError as err:
            logger.error(f"Error creating library block: {err}")

        return result

    def modify_block_olx(self, usage_key, data):
        """Modify the OLX of a library block."""
        api.set_library_block_olx(usage_key, data)

    def create_collection(self, title, description="") -> None:
        """Create a collection in the library."""
        content_library = api.require_permission_for_library_key(
            self.library_key, self.user, permissions.CAN_EDIT_THIS_CONTENT_LIBRARY
        )

        key = str(uuid4().hex[:10])

        collection = api.create_library_collection(
            library_key=content_library.library_key,
            content_library=content_library,
            collection_key=key,
            title=title,
            description=description,
            created_by=self.user.id,
        )
        return collection

    def update_library_collection_items(self, collection_key, item_keys) -> None:
        api.update_library_collection_items(
            library_key=self.library_key,
            collection_key=collection_key,
            created_by=self.user.id,
            opaque_keys=item_keys
        )
