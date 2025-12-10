"""
Tests for the ContentLibraryProcessor module.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from django.contrib.auth import get_user_model
from opaque_keys.edx.locator import LibraryLocatorV2

from openedx_ai_extensions.processors.openedx.content_libraries_processor import ContentLibraryProcessor

User = get_user_model()


@pytest.fixture
def user(db):  # pylint: disable=unused-argument
    """
    Create and return a test user.
    """
    return User.objects.create_user(
        username="testuser", email="testuser@example.com", password="password123"
    )


@pytest.fixture
def library_key():
    """
    Create and return a test library key.
    """
    return "lib:org:lib1"


@pytest.fixture
def content_library_processor(user, library_key):  # pylint: disable=redefined-outer-name
    """
    Create and return a ContentLibraryProcessor instance.
    """
    config = {
        "ContentLibraryProcessor": {
            "some_config_key": "some_value",
        }
    }
    return ContentLibraryProcessor(
        library_key=library_key, user=user, config=config
    )


# ============================================================================
# ContentLibraryProcessor Initialization Tests
# ============================================================================


@pytest.mark.django_db
def test_content_library_processor_initialization(
    user, library_key
):  # pylint: disable=redefined-outer-name
    """
    Test ContentLibraryProcessor initialization with valid config.
    """
    config = {
        "ContentLibraryProcessor": {
            "custom_setting": "test_value",
        }
    }
    processor = ContentLibraryProcessor(
        library_key=library_key, user=user, config=config
    )

    assert processor.user == user
    assert isinstance(processor.library_key, LibraryLocatorV2)
    assert str(processor.library_key) == library_key
    assert processor.config == {"custom_setting": "test_value"}


@pytest.mark.django_db
def test_content_library_processor_initialization_no_config(
    user, library_key
):  # pylint: disable=redefined-outer-name
    """
    Test ContentLibraryProcessor initialization with no config.
    """
    processor = ContentLibraryProcessor(library_key=library_key, user=user, config=None)

    assert processor.user == user
    assert isinstance(processor.library_key, LibraryLocatorV2)
    assert processor.config == {}


# ============================================================================
# ContentLibraryProcessor.create_block() Tests
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.content_libraries_processor.get_content_libraries")
def test_create_block_success(
    mock_get_content_libraries, content_library_processor
):  # pylint: disable=redefined-outer-name
    """
    Test create_block successfully creates a library block.
    """
    # Setup mocks
    mock_api = MagicMock()
    mock_serializer_class = MagicMock()
    mock_serializer_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.usage_key = "block-v1:org+lib+branch+type@problem+block@abc123"

    # Configure the mock chain
    mock_serializer_instance.is_valid.return_value = True
    mock_serializer_instance.validated_data = {
        "block_type": "problem",
        "definition_id": str(uuid4()),
    }
    mock_serializer_class.return_value = mock_serializer_instance
    mock_api.create_library_block.return_value = mock_result

    mock_content_libraries = MagicMock()
    mock_content_libraries.api = mock_api
    mock_content_libraries.rest_api.serializers.LibraryXBlockCreationSerializer = (
        mock_serializer_class
    )
    mock_get_content_libraries.return_value = mock_content_libraries

    # Test data
    block_data = {
        "block_type": "problem",
        "definition_id": str(uuid4()),
        "can_stand_alone": True,
    }

    # Execute
    result = content_library_processor.create_block(block_data)

    # Assertions
    assert result == mock_result
    mock_serializer_class.assert_called_once_with(data=block_data)
    mock_serializer_instance.is_valid.assert_called_once_with(raise_exception=True)
    mock_api.create_library_block.assert_called_once_with(
        content_library_processor.library_key,
        user_id=content_library_processor.user.id,
        **mock_serializer_instance.validated_data
    )


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.content_libraries_processor.get_content_libraries")
@patch("openedx_ai_extensions.processors.openedx.content_libraries_processor.logger")
def test_create_block_incompatible_types_error(
    mock_logger, mock_get_content_libraries, content_library_processor
):  # pylint: disable=redefined-outer-name
    """
    Test create_block handles IncompatibleTypesError gracefully.
    """
    # Setup mocks
    mock_api = MagicMock()
    mock_serializer_class = MagicMock()
    mock_serializer_instance = MagicMock()

    # Configure the mock chain
    mock_serializer_instance.is_valid.return_value = True
    mock_serializer_instance.validated_data = {
        "block_type": "problem",
        "definition_id": str(uuid4()),
    }
    mock_serializer_class.return_value = mock_serializer_instance

    # Create IncompatibleTypesError exception
    mock_api.IncompatibleTypesError = Exception
    error_message = "Incompatible block type"
    mock_api.create_library_block.side_effect = Exception(error_message)

    mock_content_libraries = MagicMock()
    mock_content_libraries.api = mock_api
    mock_content_libraries.rest_api.serializers.LibraryXBlockCreationSerializer = (
        mock_serializer_class
    )
    mock_get_content_libraries.return_value = mock_content_libraries

    # Test data
    block_data = {
        "block_type": "problem",
        "definition_id": str(uuid4()),
        "can_stand_alone": True,
    }

    # Execute - should not raise exception but log error and return None
    result = content_library_processor.create_block(block_data)

    # Assertions
    assert result is None
    mock_logger.error.assert_called()


# ============================================================================
# ContentLibraryProcessor.modify_block_olx() Tests
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.content_libraries_processor.get_content_libraries")
def test_modify_block_olx(
    mock_get_content_libraries, content_library_processor
):  # pylint: disable=redefined-outer-name
    """
    Test modify_block_olx modifies the OLX of a library block.
    """
    # Setup mocks
    mock_api = MagicMock()
    mock_content_libraries = MagicMock()
    mock_content_libraries.api = mock_api
    mock_get_content_libraries.return_value = mock_content_libraries

    usage_key = "block-v1:org+lib+branch+type@problem+block@abc123"
    olx_data = "<problem><multiplechoiceresponse></multiplechoiceresponse></problem>"

    # Execute
    content_library_processor.modify_block_olx(usage_key=usage_key, data=olx_data)

    # Assertions
    mock_api.set_library_block_olx.assert_called_once_with(usage_key, olx_data)


# ============================================================================
# ContentLibraryProcessor.create_collection() Tests
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.content_libraries_processor.get_content_libraries")
def test_create_collection(
    mock_get_content_libraries, content_library_processor
):  # pylint: disable=redefined-outer-name
    """
    Test create_collection successfully creates a collection in the library.
    """
    # Setup mocks
    mock_api = MagicMock()
    mock_permissions = MagicMock()
    mock_permissions.CAN_EDIT_THIS_CONTENT_LIBRARY = "can_edit"

    mock_content_library = MagicMock()
    mock_content_library.library_key = content_library_processor.library_key
    mock_api.require_permission_for_library_key.return_value = mock_content_library

    mock_collection = MagicMock()
    mock_collection.key = "collection-123"
    mock_api.create_library_collection.return_value = mock_collection

    mock_content_libraries = MagicMock()
    mock_content_libraries.api = mock_api
    mock_content_libraries.permissions = mock_permissions
    mock_get_content_libraries.return_value = mock_content_libraries

    # Test data
    title = "Test Collection"
    description = "A test collection for unit tests"

    # Execute
    result = content_library_processor.create_collection(
        title=title, description=description
    )

    # Assertions
    assert result == mock_collection
    mock_api.require_permission_for_library_key.assert_called_once_with(
        content_library_processor.library_key,
        content_library_processor.user,
        "can_edit",
    )
    mock_api.create_library_collection.assert_called_once()
    call_kwargs = mock_api.create_library_collection.call_args[1]
    assert call_kwargs["library_key"] == content_library_processor.library_key
    assert call_kwargs["content_library"] == mock_content_library
    assert call_kwargs["title"] == title
    assert call_kwargs["description"] == description
    assert call_kwargs["created_by"] == content_library_processor.user.id


# ============================================================================
# ContentLibraryProcessor.update_library_collection_items() Tests
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.content_libraries_processor.get_content_libraries")
def test_update_library_collection_items(
    mock_get_content_libraries, content_library_processor
):  # pylint: disable=redefined-outer-name
    """
    Test update_library_collection_items adds items to a collection.
    """
    # Setup mocks
    mock_api = MagicMock()
    mock_content_libraries = MagicMock()
    mock_content_libraries.api = mock_api
    mock_get_content_libraries.return_value = mock_content_libraries

    collection_key = "collection-123"
    item_keys = [
        "block-v1:org+lib+branch+type@problem+block@item1",
        "block-v1:org+lib+branch+type@problem+block@item2",
    ]

    # Execute
    content_library_processor.update_library_collection_items(
        collection_key=collection_key, item_keys=item_keys
    )

    # Assertions
    mock_api.update_library_collection_items.assert_called_once_with(
        library_key=content_library_processor.library_key,
        collection_key=collection_key,
        created_by=content_library_processor.user.id,
        opaque_keys=item_keys,
    )


# ============================================================================
# ContentLibraryProcessor.create_collection_and_add_items() Integration Tests
# ============================================================================


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.content_libraries_processor.get_content_libraries")
def test_create_collection_and_add_items_integration(
    mock_get_content_libraries, content_library_processor
):  # pylint: disable=redefined-outer-name
    """
    Test create_collection_and_add_items creates a collection with blocks.
    """
    # Setup mocks
    mock_api = MagicMock()
    mock_permissions = MagicMock()
    mock_permissions.CAN_EDIT_THIS_CONTENT_LIBRARY = "can_edit"
    mock_serializer_class = MagicMock()

    # Mock content library
    mock_content_library = MagicMock()
    mock_content_library.library_key = content_library_processor.library_key
    mock_api.require_permission_for_library_key.return_value = mock_content_library

    # Mock collection creation
    mock_collection = MagicMock()
    mock_collection.key = "collection-456"
    mock_api.create_library_collection.return_value = mock_collection

    # Mock block creation
    mock_block1 = MagicMock()
    mock_block1.usage_key = "block-v1:org+lib+branch+type@problem+block@block1"
    mock_block2 = MagicMock()
    mock_block2.usage_key = "block-v1:org+lib+branch+type@problem+block@block2"
    mock_api.create_library_block.side_effect = [mock_block1, mock_block2]

    # Mock serializer
    mock_serializer_instance = MagicMock()
    mock_serializer_instance.is_valid.return_value = True
    mock_serializer_instance.validated_data = {}
    mock_serializer_class.return_value = mock_serializer_instance

    mock_content_libraries = MagicMock()
    mock_content_libraries.api = mock_api
    mock_content_libraries.permissions = mock_permissions
    mock_content_libraries.rest_api.serializers.LibraryXBlockCreationSerializer = (
        mock_serializer_class
    )
    mock_get_content_libraries.return_value = mock_content_libraries

    # Test data
    items = [
        {
            "category": "problem",
            "data": "<problem><multiplechoiceresponse></multiplechoiceresponse></problem>",
        },
        {
            "category": "problem",
            "data": "<problem><numericalresponse></numericalresponse></problem>",
        },
    ]
    title = "Integration Test Collection"
    description = "Collection created via integration test"

    # Execute
    result = content_library_processor.create_collection_and_add_items(
        items=items, title=title, description=description
    )

    # Assertions
    assert result == str(mock_collection.key)
    assert mock_api.create_library_collection.call_count == 1
    assert mock_api.create_library_block.call_count == 2
    assert mock_api.set_library_block_olx.call_count == 2
    assert mock_api.update_library_collection_items.call_count == 1

    # Verify update_library_collection_items was called with correct keys
    update_call = mock_api.update_library_collection_items.call_args[1]
    assert update_call["collection_key"] == mock_collection.key
    assert len(update_call["opaque_keys"]) == 2
    assert mock_block1.usage_key in update_call["opaque_keys"]
    assert mock_block2.usage_key in update_call["opaque_keys"]


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.content_libraries_processor.get_content_libraries")
def test_create_collection_and_add_items_with_empty_items(
    mock_get_content_libraries, content_library_processor
):  # pylint: disable=redefined-outer-name
    """
    Test create_collection_and_add_items handles empty items list.
    """
    # Setup mocks
    mock_api = MagicMock()
    mock_permissions = MagicMock()
    mock_permissions.CAN_EDIT_THIS_CONTENT_LIBRARY = "can_edit"

    # Mock content library
    mock_content_library = MagicMock()
    mock_content_library.library_key = content_library_processor.library_key
    mock_api.require_permission_for_library_key.return_value = mock_content_library

    # Mock collection creation
    mock_collection = MagicMock()
    mock_collection.key = "collection-empty"
    mock_api.create_library_collection.return_value = mock_collection

    mock_content_libraries = MagicMock()
    mock_content_libraries.api = mock_api
    mock_content_libraries.permissions = mock_permissions
    mock_get_content_libraries.return_value = mock_content_libraries

    # Test data
    items = []
    title = "Empty Collection"
    description = "Collection with no items"

    # Execute
    result = content_library_processor.create_collection_and_add_items(
        items=items, title=title, description=description
    )

    # Assertions
    assert result == str(mock_collection.key)
    assert mock_api.create_library_collection.call_count == 1
    assert mock_api.create_library_block.call_count == 0
    assert mock_api.set_library_block_olx.call_count == 0
    # Should not try to update collection items if no blocks were created
    assert mock_api.update_library_collection_items.call_count == 0


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.content_libraries_processor.get_content_libraries")
def test_modify_block_olx_with_special_characters(
    mock_get_content_libraries, content_library_processor
):  # pylint: disable=redefined-outer-name
    """
    Test modify_block_olx handles OLX data with special characters and attributes.
    """
    # Setup mocks
    mock_api = MagicMock()
    mock_content_libraries = MagicMock()
    mock_content_libraries.api = mock_api
    mock_get_content_libraries.return_value = mock_content_libraries

    usage_key = "block-v1:org+lib+branch+type@problem+block@special123"
    olx_data = """<problem display_name="Test Problem with &amp; special chars" max_attempts="3">
    <multiplechoiceresponse>
        <p>Question with &lt;special&gt; characters &amp; symbols: α, β, γ</p>
        <label>Select the correct answer:</label>
        <choicegroup type="MultipleChoice">
            <choice correct="true">Answer with "quotes" &amp; symbols</choice>
            <choice correct="false">Wrong answer</choice>
        </choicegroup>
    </multiplechoiceresponse>
</problem>"""

    # Execute
    content_library_processor.modify_block_olx(usage_key=usage_key, data=olx_data)

    # Assertions
    mock_api.set_library_block_olx.assert_called_once_with(usage_key, olx_data)
    # Verify the exact data passed includes special characters
    call_args = mock_api.set_library_block_olx.call_args[0]
    assert "&amp;" in call_args[1]
    assert "&lt;" in call_args[1]
    assert "α, β, γ" in call_args[1]


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.content_libraries_processor.get_content_libraries")
def test_update_library_collection_items_with_multiple_blocks(
    mock_get_content_libraries, content_library_processor
):  # pylint: disable=redefined-outer-name
    """
    Test update_library_collection_items handles multiple block keys correctly.
    """
    # Setup mocks
    mock_api = MagicMock()
    mock_content_libraries = MagicMock()
    mock_content_libraries.api = mock_api
    mock_get_content_libraries.return_value = mock_content_libraries

    collection_key = "collection-multi"
    item_keys = [
        "block-v1:org+lib+branch+type@problem+block@item1",
        "block-v1:org+lib+branch+type@html+block@item2",
        "block-v1:org+lib+branch+type@video+block@item3",
        "block-v1:org+lib+branch+type@problem+block@item4",
    ]

    # Execute
    content_library_processor.update_library_collection_items(
        collection_key=collection_key, item_keys=item_keys
    )

    # Assertions
    mock_api.update_library_collection_items.assert_called_once()
    call_kwargs = mock_api.update_library_collection_items.call_args[1]
    assert call_kwargs["library_key"] == content_library_processor.library_key
    assert call_kwargs["collection_key"] == collection_key
    assert call_kwargs["created_by"] == content_library_processor.user.id
    assert call_kwargs["opaque_keys"] == item_keys
    assert len(call_kwargs["opaque_keys"]) == 4


@pytest.mark.django_db
@patch("openedx_ai_extensions.processors.openedx.content_libraries_processor.get_content_libraries")
def test_create_block_with_validation_error(
    mock_get_content_libraries, content_library_processor
):  # pylint: disable=redefined-outer-name
    """
    Test create_block raises exception when serializer validation fails.
    """
    # Setup mocks
    mock_api = MagicMock()
    mock_serializer_class = MagicMock()
    mock_serializer_instance = MagicMock()

    # Configure the mock chain - serializer validation fails
    mock_serializer_instance.is_valid.side_effect = Exception("Invalid block data")
    mock_serializer_class.return_value = mock_serializer_instance

    mock_content_libraries = MagicMock()
    mock_content_libraries.api = mock_api
    mock_content_libraries.rest_api.serializers.LibraryXBlockCreationSerializer = (
        mock_serializer_class
    )
    mock_get_content_libraries.return_value = mock_content_libraries

    # Test data with invalid structure
    block_data = {
        "block_type": "invalid_type",
        "definition_id": "not-a-uuid",
    }

    # Execute - should raise Exception
    with pytest.raises(Exception, match="Invalid block data"):
        content_library_processor.create_block(block_data)

    # Assertions
    mock_serializer_class.assert_called_once_with(data=block_data)
    mock_serializer_instance.is_valid.assert_called_once_with(raise_exception=True)
    mock_api.create_library_block.assert_not_called()
