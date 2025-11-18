from openedx.core.djangoapps.content_libraries.rest_api import serializers
from openedx.core.djangoapps.content_libraries import api, permissions

import logging

from opaque_keys.edx.locator import LibraryLocatorV2


logger = logging.getLogger(__name__)

def create_container(lib_key_str: str, user, data) -> None:
    library_key = LibraryLocatorV2.from_string(lib_key_str)
    api.require_permission_for_library_key(library_key, user, permissions.CAN_EDIT_THIS_CONTENT_LIBRARY)
    serializer = serializers.LibraryContainerMetadataSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    container_type = serializer.validated_data['container_type']
    container = api.create_container(
        library_key,
        container_type,
        title=serializer.validated_data['display_name'],
        slug=serializer.validated_data.get('slug'),
        user_id=user.id,
    )
    return container


def create_block(lib_key_str: str, user, data):
    library_key = LibraryLocatorV2.from_string(lib_key_str)
    api.require_permission_for_library_key(library_key, user, permissions.CAN_EDIT_THIS_CONTENT_LIBRARY)
    serializer = serializers.LibraryXBlockCreationSerializer(data=data)
    serializer.is_valid(raise_exception=True)

    try:
        result = api.create_library_block(library_key, user_id=user.id, **serializer.validated_data)
    except api.IncompatibleTypesError as err:
        logger.error(f"Error creating library block: {err}")

    return result

def modify_block_olx(usage_key, data, user):
    api.set_library_block_olx(usage_key, data['data'])


def publish_changes(lib_key_str: str, user) -> None:
    library_key = LibraryLocatorV2.from_string(lib_key_str)
    api.publish_changes(library_key, user_id=user.id)
