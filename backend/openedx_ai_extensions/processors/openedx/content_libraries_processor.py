"""
Utility functions and classes for content library operations.
"""
import logging
from uuid import uuid4

from opaque_keys.edx.locator import LibraryLocatorV2

from openedx_ai_extensions.edxapp_wrapper.content_libraries_module import get_content_libraries

logger = logging.getLogger(__name__)


class ContentLibraryProcessor:
    """
    Helper class for content library operations
    """
    def __init__(self, library_key: str, user, config=None) -> None:
        config = config or {}
        self.library_key = LibraryLocatorV2.from_string(library_key)
        self.user = user

        # Find specific config using class name
        class_name = self.__class__.__name__
        self.config = config.get(class_name, {})

    def create_collection_and_add_items(self, items, title, description="") -> str:
        """Create a collection and add items to it."""
        collection = self.create_collection(title=title, description=description)

        if not collection:
            logger.error("Failed to create collection.")
            raise Exception("Collection creation failed.")

        opaque_keys = []
        for problem_info in items:

            block_data = {
              "block_type": problem_info['category'],
              "definition_id": str(uuid4()),
              "can_stand_alone": True,
            }

            try:
                problem = self.create_block(block_data)
                if problem:
                    self.modify_block_olx(usage_key=problem.usage_key, data=problem_info['data'])

                opaque_keys.append(problem.usage_key)
            except Exception as e:  # pylint: disable=broad-exception-caught
                if problem:
                    self.delete_block(problem.usage_key)
                logger.error(f"Error creating or modifying block: {e}")
                continue

        if not opaque_keys:
            logger.warning("No items were created to add to the collection.")
            return str(collection.key)

        self.update_library_collection_items(
            collection_key=collection.key,
            item_keys=opaque_keys
        )
        return str(collection.key)

    def delete_block(self, usage_key):
        """Delete a library block."""
        api = get_content_libraries().api
        api.delete_library_block(usage_key, user_id=self.user.id)

    def create_block(self, data):
        """Create a library block."""
        api = get_content_libraries().api
        serializers = get_content_libraries().rest_api.serializers

        serializer = serializers.LibraryXBlockCreationSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        try:
            result = api.create_library_block(self.library_key, user_id=self.user.id, **serializer.validated_data)
        except api.IncompatibleTypesError as err:
            logger.error(f"Error creating library block: {err}")
            return None

        return result

    def modify_block_olx(self, usage_key, data):
        """Modify the OLX of a library block."""
        api = get_content_libraries().api
        api.set_library_block_olx(usage_key, data)

    def create_collection(self, title, description="") -> None:
        """Create a collection in the library."""
        api = get_content_libraries().api
        permissions = get_content_libraries().permissions

        content_library = api.require_permission_for_library_key(
            self.library_key, self.user, permissions.CAN_EDIT_THIS_CONTENT_LIBRARY
        )

        key = str(uuid4().hex[:10])

        try:
            collection = api.create_library_collection(
                library_key=content_library.library_key,
                content_library=content_library,
                collection_key=key,
                title=title,
                description=description,
                created_by=self.user.id,
            )
            return collection
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error creating collection: {e}")
            return None

    def update_library_collection_items(self, collection_key, item_keys) -> None:
        """Modifies the list of items in a collection."""
        api = get_content_libraries().api

        api.update_library_collection_items(
            library_key=self.library_key,
            collection_key=collection_key,
            created_by=self.user.id,
            opaque_keys=item_keys
        )
