"""
Tests for openedx_ai_extensions.workflows.template_utils module.
"""
import shutil
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings

from openedx_ai_extensions.models import PromptTemplate
from openedx_ai_extensions.workflows.template_utils import (
    WORKFLOW_SCHEMA,
    _validate_prompt_templates,
    _validate_semantics,
    discover_templates,
    get_effective_config,
    get_template_directories,
    is_safe_template_path,
    load_template,
    merge_template_with_patch,
    parse_json5_string,
    validate_workflow_config,
)


class TestGetTemplateDirectories(TestCase):
    """Tests for get_template_directories function."""

    def test_empty_directory_list(self):
        """Test that when WORKFLOW_TEMPLATE_DIRS is empty list, returns empty list."""
        # When WORKFLOW_TEMPLATE_DIRS is explicitly set to empty list
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[]):
            dirs = get_template_directories()

            # Should return empty list
            self.assertIsInstance(dirs, list)
            self.assertEqual(dirs, [])

    def test_custom_directories_from_settings(self):
        """Test that custom directories are read from settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with override_settings(WORKFLOW_TEMPLATE_DIRS=[tmpdir]):
                dirs = get_template_directories()

                self.assertEqual(len(dirs), 1)
                self.assertEqual(dirs[0], Path(tmpdir).resolve())

    def test_nonexistent_directory_warning(self):
        """Test that nonexistent directories are filtered out with warning."""
        fake_dir = "/nonexistent/fake/directory/path"
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[fake_dir]):
            with self.assertLogs('openedx_ai_extensions.workflows.template_utils', level='WARNING') as cm:
                dirs = get_template_directories()

                self.assertEqual(len(dirs), 0)
                self.assertTrue(any("does not exist" in msg for msg in cm.output))

    def test_multiple_directories(self):
        """Test handling multiple template directories."""
        with tempfile.TemporaryDirectory() as tmpdir1:
            with tempfile.TemporaryDirectory() as tmpdir2:
                with override_settings(WORKFLOW_TEMPLATE_DIRS=[tmpdir1, tmpdir2]):
                    dirs = get_template_directories()

                    self.assertEqual(len(dirs), 2)
                    self.assertIn(Path(tmpdir1).resolve(), dirs)
                    self.assertIn(Path(tmpdir2).resolve(), dirs)


class TestIsSafeTemplatePath(TestCase):
    """Tests for is_safe_template_path function."""

    def setUp(self):
        """Create temporary directory for testing."""
        self.tmpdir = tempfile.mkdtemp()
        self.temp_path = Path(self.tmpdir)

        # Create a test file
        self.test_file = self.temp_path / "test_template.json"
        self.test_file.write_text('{"test": "data"}')

        # Create nested directory with file
        nested_dir = self.temp_path / "nested"
        nested_dir.mkdir()
        self.nested_file = nested_dir / "nested_template.json"
        self.nested_file.write_text('{"nested": "data"}')

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.tmpdir)

    def test_empty_path_rejected(self):
        """Test that empty path is rejected."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            self.assertFalse(is_safe_template_path(""))
            self.assertFalse(is_safe_template_path(None))

    def test_path_traversal_rejected(self):
        """Test that path traversal attempts are rejected."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            self.assertFalse(is_safe_template_path("../etc/passwd"))
            self.assertFalse(is_safe_template_path("foo/../../../etc/passwd"))
            self.assertFalse(is_safe_template_path("foo/bar/../baz"))

    def test_absolute_path_rejected(self):
        """Test that absolute paths are rejected."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            self.assertFalse(is_safe_template_path("/etc/passwd"))
            self.assertFalse(is_safe_template_path("/tmp/template.json"))

    def test_valid_relative_path_accepted(self):
        """Test that valid relative paths are accepted."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            self.assertTrue(is_safe_template_path("test_template.json"))
            self.assertTrue(is_safe_template_path("nested/nested_template.json"))

    def test_nonexistent_file_rejected(self):
        """Test that nonexistent files are rejected."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            self.assertFalse(is_safe_template_path("nonexistent.json"))

    def test_directory_path_rejected(self):
        """Test that directory paths are rejected (must be files)."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            self.assertFalse(is_safe_template_path("nested"))


class TestDiscoverTemplates(TestCase):
    """Tests for discover_templates function."""

    def setUp(self):
        """Create temporary directory with test templates."""
        self.tmpdir = tempfile.mkdtemp()
        self.temp_path = Path(self.tmpdir)

        # Create test templates
        (self.temp_path / "template1.json").write_text('{}')
        (self.temp_path / "template2.json").write_text('{}')

        # Create nested templates
        nested_dir = self.temp_path / "category"
        nested_dir.mkdir()
        (nested_dir / "template3.json").write_text('{}')

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.tmpdir)

    def test_discover_all_templates(self):
        """Test discovering all templates in directory."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            templates = discover_templates()

            self.assertEqual(len(templates), 3)

            # Check structure: list of (path, display_name) tuples
            for template in templates:
                self.assertIsInstance(template, tuple)
                self.assertEqual(len(template), 2)
                path, display_name = template
                self.assertIsInstance(path, str)
                self.assertIsInstance(display_name, str)
                # Path should include .json extension
                self.assertTrue(path.endswith('.json'))
                # Display name should not include .json extension
                self.assertFalse(display_name.endswith('.json'))

    def test_templates_sorted_by_display_name(self):
        """Test that templates are sorted by display name."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            templates = discover_templates()

            display_names = [t[1] for t in templates]
            self.assertEqual(display_names, sorted(display_names))

    def test_empty_directory(self):
        """Test discovering templates in empty directory."""
        with tempfile.TemporaryDirectory() as empty_dir:
            with override_settings(WORKFLOW_TEMPLATE_DIRS=[empty_dir]):
                templates = discover_templates()
                self.assertEqual(len(templates), 0)

    def test_multiple_templates_in_nested_dirs(self):
        """Test discovering templates in nested directories."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            templates = discover_templates()
            # Should discover all templates including nested ones
            self.assertGreaterEqual(len(templates), 3)

            # Verify nested template has correct path format
            nested = [t for t in templates if 'category' in t[0]]
            self.assertGreater(len(nested), 0)


class TestLoadTemplate(TestCase):
    """Tests for load_template function."""

    def setUp(self):
        """Create temporary directory with test templates."""
        self.tmpdir = tempfile.mkdtemp()
        self.temp_path = Path(self.tmpdir)

        # Create valid JSON5 template
        self.valid_template = self.temp_path / "valid.json"
        self.valid_template.write_text('''
        {
            // This is a comment
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {},
            "actuator_config": {},
        }
        ''')

        # Create invalid JSON template
        self.invalid_template = self.temp_path / "invalid.json"
        self.invalid_template.write_text('{ invalid json }')

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.tmpdir)

    def test_load_valid_template(self):
        """Test loading a valid template."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            data = load_template("valid.json")

            self.assertIsNotNone(data)
            self.assertIsInstance(data, dict)
            self.assertEqual(data["orchestrator_class"], "TestOrchestrator")

    def test_load_unsafe_path_rejected(self):
        """Test that unsafe paths are rejected."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            data = load_template("../etc/passwd")
            self.assertIsNone(data)

    def test_load_nonexistent_template(self):
        """Test loading nonexistent template returns None."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            data = load_template("nonexistent.json")
            self.assertIsNone(data)

    def test_load_invalid_json(self):
        """Test loading invalid JSON returns None."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            data = load_template("invalid.json")
            self.assertIsNone(data)

    def test_load_template_with_comments(self):
        """Test that JSON5 comments are properly handled."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            data = load_template("valid.json")

            # Should load successfully despite comments
            self.assertIsNotNone(data)
            self.assertIn("orchestrator_class", data)


class TestParseJson5String(TestCase):
    """Tests for parse_json5_string function."""

    def test_parse_valid_json5(self):
        """Test parsing valid JSON5 string."""
        json5_str = '''
        {
            // Comment
            "key": "value",
            "number": 123,
        }
        '''
        result = parse_json5_string(json5_str)

        self.assertEqual(result["key"], "value")
        self.assertEqual(result["number"], 123)

    def test_parse_empty_string(self):
        """Test parsing empty string returns empty dict."""
        self.assertEqual(parse_json5_string(""), {})
        self.assertEqual(parse_json5_string("   "), {})

    def test_parse_invalid_json5_raises_error(self):
        """Test that invalid JSON5 raises appropriate error."""
        # json5 raises ValueError for invalid JSON5
        with self.assertRaises(ValueError):
            parse_json5_string("{ invalid }")

    def test_parse_standard_json(self):
        """Test parsing standard JSON works."""
        json_str = '{"key": "value", "list": [1, 2, 3]}'
        result = parse_json5_string(json_str)

        self.assertEqual(result["key"], "value")
        self.assertEqual(result["list"], [1, 2, 3])


class TestMergeTemplateWithPatch(TestCase):
    """Tests for merge_template_with_patch function."""

    def test_merge_empty_patch(self):
        """Test merging with empty patch returns copy of base."""
        base = {"key": "value", "nested": {"a": 1}}
        result = merge_template_with_patch(base, {})

        self.assertEqual(result, base)
        # Should be a copy, not the same object
        self.assertIsNot(result, base)

    def test_merge_none_patch(self):
        """Test merging with None patch returns copy of base."""
        base = {"key": "value"}
        result = merge_template_with_patch(base, None)

        self.assertEqual(result, base)
        self.assertIsNot(result, base)

    def test_merge_simple_patch(self):
        """Test merging simple patch."""
        base = {"a": 1, "b": 2}
        patch = {"b": 3, "c": 4}
        result = merge_template_with_patch(base, patch)

        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"], 3)  # Overridden
        self.assertEqual(result["c"], 4)  # Added

    def test_merge_nested_patch(self):
        """Test merging nested objects."""
        base = {
            "processor_config": {
                "model": "gpt-3.5",
                "temperature": 0.7
            }
        }
        patch = {
            "processor_config": {
                "temperature": 0.9,
                "max_tokens": 1000
            }
        }
        result = merge_template_with_patch(base, patch)

        self.assertEqual(result["processor_config"]["model"], "gpt-3.5")
        self.assertEqual(result["processor_config"]["temperature"], 0.9)
        self.assertEqual(result["processor_config"]["max_tokens"], 1000)

    def test_merge_with_null_value(self):
        """Test that null values in patch are preserved."""
        base = {"a": 1, "b": 2, "c": 3}
        patch = {"b": None}
        result = merge_template_with_patch(base, patch)

        # jsonmerge preserves None values by default
        self.assertEqual(result["a"], 1)
        self.assertEqual(result["b"], None)
        self.assertEqual(result["c"], 3)


class TestValidateWorkflowConfig(TestCase):
    """Tests for validate_workflow_config function."""

    def test_validate_valid_config(self):
        """Test validating a valid schema 1.0 configuration."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {
                "LLMProcessor": {"function": "summarize_content"}
            },
            "actuator_config": {
                "UIComponents": {
                    "request": {},
                    "response": {}
                }
            }
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertTrue(is_valid, f"Validation failed with errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_validate_null_config(self):
        """Test validating null config."""
        is_valid, errors = validate_workflow_config(None)

        self.assertFalse(is_valid)
        self.assertIn("null", errors[0].lower())

    def test_validate_non_dict_config(self):
        """Test validating non-dict config."""
        is_valid, errors = validate_workflow_config("not a dict")

        self.assertFalse(is_valid)
        self.assertIn("dict", errors[0].lower())

    def test_validate_missing_required_fields(self):
        """Test that missing required fields are caught."""
        config = {"orchestrator_class": "Test"}
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        # Should complain about missing schema_version, processor_config, and actuator_config
        self.assertGreater(len(errors), 0)

    def test_validate_missing_schema_version(self):
        """Test that missing schema_version is invalid."""
        config = {
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {"LLMProcessor": {}},
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("schema_version" in err for err in errors))

    def test_validate_wrong_schema_version(self):
        """Test that wrong schema_version is invalid."""
        config = {
            "schema_version": "2.0",
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {"LLMProcessor": {}},
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("1.0" in err for err in errors))

    def test_validate_empty_processor_config(self):
        """Test that empty processor_config is invalid in schema 1.0."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {},
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("at least one processor" in err or "minProperties" in err for err in errors))

    def test_validate_processor_config_with_any_processor(self):
        """Test that processor_config accepts any processor, not just LLMProcessor."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {
                "EducatorAssistantProcessor": {"function": "generate_quiz"}
            },
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertTrue(is_valid, f"Validation failed with errors: {errors}")

    def test_validate_processor_config_with_non_object_processor(self):
        """Test that processor values must be objects."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {
                "LLMProcessor": "not an object"
            },
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("LLMProcessor" in err and "object" in err for err in errors))

    def test_validate_missing_ui_components(self):
        """Test that missing UIComponents is invalid in schema 1.0."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {"LLMProcessor": {}},
            "actuator_config": {}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("UIComponents" in err for err in errors))

    def test_validate_missing_request_in_ui_components(self):
        """Test that missing request is invalid in schema 1.0."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {"LLMProcessor": {}},
            "actuator_config": {"UIComponents": {"response": {}}}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("request" in err for err in errors))

    def test_validate_missing_response_in_ui_components(self):
        """Test that missing response is invalid in schema 1.0."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {"LLMProcessor": {}},
            "actuator_config": {"UIComponents": {"request": {}}}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("response" in err for err in errors))

    def test_validate_empty_orchestrator_class(self):
        """Test that empty orchestrator_class is invalid."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "",
            "processor_config": {"LLMProcessor": {}},
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("orchestrator_class" in err and "empty" in err for err in errors))

    def test_validate_invalid_orchestrator_class_identifier(self):
        """Test that invalid Python identifier is caught."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "Invalid-Class-Name!",
            "processor_config": {"LLMProcessor": {}},
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("identifier" in err.lower() for err in errors))

    def test_validate_processor_config_not_dict(self):
        """Test that non-dict processor_config is invalid."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "TestOrchestrator",
            "processor_config": "not a dict",
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("processor_config" in err for err in errors))

    def test_validate_actuator_config_not_dict(self):
        """Test that non-dict actuator_config is invalid."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {"LLMProcessor": {}},
            "actuator_config": ["not", "a", "dict"]
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("actuator_config" in err for err in errors))

    def test_validate_ui_components_not_dict(self):
        """Test that non-dict UIComponents is invalid."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {"LLMProcessor": {}},
            "actuator_config": {
                "UIComponents": "not a dict"
            }
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("UIComponents" in err for err in errors))

    def test_validate_additional_properties_allowed(self):
        """Test that additional properties are allowed."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {"LLMProcessor": {}},
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}},
            "custom_field": "custom_value"
        }
        is_valid, _errors = validate_workflow_config(config)

        # Should be valid - additional properties are allowed
        self.assertTrue(is_valid)


class TestValidateSemantics(TestCase):
    """Tests for _validate_semantics function."""

    def test_valid_config_no_errors(self):
        """Test that valid config produces no errors."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "ValidOrchestrator",
            "processor_config": {"LLMProcessor": {}},
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}}
        }
        errors = _validate_semantics(config)

        self.assertEqual(len(errors), 0)

    def test_orchestrator_class_with_underscores(self):
        """Test that underscores in orchestrator_class are allowed."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "My_Test_Orchestrator",
            "processor_config": {"LLMProcessor": {}},
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}}
        }
        errors = _validate_semantics(config)

        self.assertEqual(len(errors), 0)

    def test_empty_orchestrator_class(self):
        """Test that empty orchestrator_class produces error."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "",
            "processor_config": {"LLMProcessor": {}},
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}}
        }
        errors = _validate_semantics(config)

        self.assertGreater(len(errors), 0)
        self.assertTrue(any("empty" in err for err in errors))

    def test_invalid_identifier_special_chars(self):
        """Test that special characters in orchestrator_class are rejected."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "Invalid@Orchestrator!",
            "processor_config": {"LLMProcessor": {}},
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}}
        }
        errors = _validate_semantics(config)

        self.assertGreater(len(errors), 0)


class TestValidatePromptTemplates(TestCase):
    """Tests for _validate_prompt_templates function."""

    def test_no_prompt_template_no_errors(self):
        """Test that configs without prompt_template produce no errors."""
        processor_config = {
            "LLMProcessor": {"function": "summarize_content", "provider": "default"},
            "OpenEdXProcessor": {"function": "get_location_content"},
        }
        errors = _validate_prompt_templates(processor_config)
        self.assertEqual(errors, [])

    def test_existing_slug_no_errors(self):
        """Test that referencing an existing prompt template by slug produces no errors."""
        template = PromptTemplate.objects.create(
            slug="test-existing-slug",
            body="You are a helpful AI assistant."
        )
        processor_config = {
            "LLMProcessor": {"prompt_template": template.slug},
        }
        errors = _validate_prompt_templates(processor_config)
        self.assertEqual(errors, [])

    def test_existing_uuid_no_errors(self):
        """Test that referencing an existing prompt template by UUID produces no errors."""
        template = PromptTemplate.objects.create(
            slug="test-existing-uuid",
            body="You are a helpful AI assistant."
        )
        processor_config = {
            "LLMProcessor": {"prompt_template": str(template.id)},
        }
        errors = _validate_prompt_templates(processor_config)
        self.assertEqual(errors, [])

    def test_nonexistent_slug_produces_error(self):
        """Test that referencing a nonexistent slug produces a validation error."""
        processor_config = {
            "LLMProcessor": {"prompt_template": "slug-que-no-existe"},
        }
        errors = _validate_prompt_templates(processor_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("slug-que-no-existe", errors[0])
        self.assertIn("does not exist", errors[0])
        self.assertIn("LLMProcessor", errors[0])

    def test_nonexistent_uuid_produces_error(self):
        """Test that referencing a nonexistent UUID produces a validation error."""
        processor_config = {
            "LLMProcessor": {"prompt_template": "12345678-1234-1234-1234-123456789abc"},
        }
        errors = _validate_prompt_templates(processor_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("12345678-1234-1234-1234-123456789abc", errors[0])
        self.assertIn("does not exist", errors[0])

    def test_multiple_processors_with_invalid_templates(self):
        """Test that errors are reported for each processor with an invalid prompt_template."""
        processor_config = {
            "LLMProcessor": {"prompt_template": "nonexistent-1"},
            "EducatorAssistantProcessor": {"prompt_template": "nonexistent-2"},
        }
        errors = _validate_prompt_templates(processor_config)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("nonexistent-1" in e for e in errors))
        self.assertTrue(any("nonexistent-2" in e for e in errors))

    def test_mixed_valid_and_invalid_templates(self):
        """Test mix of valid and invalid prompt_template references."""
        template = PromptTemplate.objects.create(
            slug="valid-template",
            body="A valid prompt."
        )
        processor_config = {
            "LLMProcessor": {"prompt_template": template.slug},
            "EducatorAssistantProcessor": {"prompt_template": "invalid-template"},
        }
        errors = _validate_prompt_templates(processor_config)
        self.assertEqual(len(errors), 1)
        self.assertIn("invalid-template", errors[0])
        self.assertIn("EducatorAssistantProcessor", errors[0])

    def test_empty_prompt_template_no_errors(self):
        """Test that empty string or null prompt_template is skipped (no error)."""
        processor_config = {
            "LLMProcessor": {"prompt_template": ""},
            "OpenEdXProcessor": {"prompt_template": None},
        }
        errors = _validate_prompt_templates(processor_config)
        self.assertEqual(errors, [])

    def test_non_dict_processor_value_skipped(self):
        """Test that non-dict processor values are skipped without error."""
        processor_config = {
            "LLMProcessor": "not a dict",
        }
        errors = _validate_prompt_templates(processor_config)
        self.assertEqual(errors, [])

    def test_full_validation_catches_nonexistent_prompt_template(self):
        """Test that validate_workflow_config catches nonexistent prompt_template (integration)."""
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "DirectLLMResponse",
            "processor_config": {
                "LLMProcessor": {"prompt_template": "does-not-exist"},
            },
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}},
        }
        is_valid, errors = validate_workflow_config(config)
        self.assertFalse(is_valid)
        self.assertTrue(any("does-not-exist" in e for e in errors))

    def test_full_validation_passes_with_existing_prompt_template(self):
        """Test that validate_workflow_config passes with an existing prompt_template."""
        PromptTemplate.objects.create(
            slug="real-template",
            body="This prompt exists."
        )
        config = {
            "schema_version": "1.0",
            "orchestrator_class": "DirectLLMResponse",
            "processor_config": {
                "LLMProcessor": {"prompt_template": "real-template"},
            },
            "actuator_config": {"UIComponents": {"request": {}, "response": {}}},
        }
        is_valid, errors = validate_workflow_config(config)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])


class TestGetEffectiveConfig(TestCase):
    """Tests for get_effective_config function."""

    def setUp(self):
        """Create temporary directory with test template."""
        self.tmpdir = tempfile.mkdtemp()
        self.temp_path = Path(self.tmpdir)

        # Create base template
        self.base_template = self.temp_path / "base.json"
        self.base_template.write_text('''
        {
            "orchestrator_class": "BaseOrchestrator",
            "processor_config": {
                "model": "gpt-3.5",
                "temperature": 0.7
            },
            "actuator_config": {
                "type": "basic"
            }
        }
        ''')

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.tmpdir)

    def test_get_effective_config_no_patch(self):
        """Test getting effective config with no patch."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            config = get_effective_config("base.json", {})

            self.assertIsNotNone(config)
            self.assertEqual(config["orchestrator_class"], "BaseOrchestrator")

    def test_get_effective_config_with_patch(self):
        """Test getting effective config with patch."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            patch = {
                "processor_config": {
                    "temperature": 0.9
                }
            }
            config = get_effective_config("base.json", patch)

            self.assertIsNotNone(config)
            self.assertEqual(config["processor_config"]["temperature"], 0.9)
            self.assertEqual(config["processor_config"]["model"], "gpt-3.5")

    def test_get_effective_config_nonexistent_template(self):
        """Test getting effective config for nonexistent template."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            config = get_effective_config("nonexistent.json", {})

            self.assertIsNone(config)

    def test_get_effective_config_none_patch(self):
        """Test getting effective config with None patch."""
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            config = get_effective_config("base.json", None)

            self.assertIsNotNone(config)
            self.assertEqual(config["orchestrator_class"], "BaseOrchestrator")


class TestValidateAllProfiles(TestCase):
    """Tests to validate all profile templates in the codebase."""

    def test_all_profile_templates_are_valid(self):
        """Test that all profile templates pass schema 1.0 validation."""
        # Get the profiles directory
        profiles_dir = Path(__file__).parent.parent / "openedx_ai_extensions" / "workflows" / "profiles"

        if not profiles_dir.exists():
            self.skipTest(f"Profiles directory not found: {profiles_dir}")

        # Find all JSON files in the profiles directory
        json_files = list(profiles_dir.rglob("*.json"))

        self.assertGreater(len(json_files), 0, "No profile JSON files found to validate")

        # Track validation results
        validation_errors = {}
        successful_validations = []

        # Test each profile template
        with override_settings(WORKFLOW_TEMPLATE_DIRS=[str(profiles_dir)]):
            for json_file in json_files:
                # Get relative path from profiles directory
                rel_path = json_file.relative_to(profiles_dir)

                # Load the template
                template_data = load_template(str(rel_path))

                if template_data is None:
                    validation_errors[str(rel_path)] = ["Failed to load template (invalid JSON5 or read error)"]
                    continue

                # Validate the template
                is_valid, errors = validate_workflow_config(template_data)

                if not is_valid:
                    validation_errors[str(rel_path)] = errors
                else:
                    successful_validations.append(str(rel_path))

        # Report results
        if validation_errors:
            error_report = "\n\n=== PROFILE VALIDATION FAILURES ===\n"
            for template_path, errors in validation_errors.items():
                error_report += f"\n{template_path}:\n"
                for error in errors:
                    error_report += f"  - {error}\n"

            self.fail(
                f"{len(validation_errors)} out of {len(json_files)} profile templates failed validation."
                f"{error_report}\n\n"
                f"Successfully validated: {len(successful_validations)} templates"
            )

        # All templates are valid
        print(f"\n✓ Successfully validated {len(successful_validations)} profile templates")
        for path in sorted(successful_validations):
            print(f"  ✓ {path}")


class TestWorkflowSchema(TestCase):
    """Tests for WORKFLOW_SCHEMA (version 1.0)."""

    def test_schema_has_required_fields(self):
        """Test that schema defines all required top-level fields."""
        self.assertIn("required", WORKFLOW_SCHEMA)
        required = WORKFLOW_SCHEMA["required"]

        self.assertIn("schema_version", required)
        self.assertIn("orchestrator_class", required)
        self.assertIn("processor_config", required)
        self.assertIn("actuator_config", required)

    def test_schema_properties_defined(self):
        """Test that schema has all property definitions."""
        self.assertIn("properties", WORKFLOW_SCHEMA)
        properties = WORKFLOW_SCHEMA["properties"]

        self.assertIn("orchestrator_class", properties)
        self.assertIn("processor_config", properties)
        self.assertIn("actuator_config", properties)
        self.assertIn("schema_version", properties)

    def test_schema_allows_additional_properties(self):
        """Test that schema allows additional properties."""
        self.assertTrue(WORKFLOW_SCHEMA.get("additionalProperties", False))

    def test_schema_version_constrained_to_1_0(self):
        """Test that schema_version must be exactly '1.0'."""
        schema_version_prop = WORKFLOW_SCHEMA["properties"]["schema_version"]
        self.assertEqual(schema_version_prop.get("const"), "1.0")

    def test_processor_config_requires_at_least_one_processor(self):
        """Test that processor_config must have at least one processor."""
        processor_config_props = WORKFLOW_SCHEMA["properties"]["processor_config"]

        # Must have minProperties constraint
        self.assertIn("minProperties", processor_config_props)
        self.assertEqual(processor_config_props["minProperties"], 1)

        # Should allow additional properties (any processor)
        self.assertTrue(processor_config_props.get("additionalProperties", False))

    def test_actuator_config_requires_ui_components(self):
        """Test that actuator_config must have UIComponents."""
        actuator_config_props = WORKFLOW_SCHEMA["properties"]["actuator_config"]
        self.assertIn("required", actuator_config_props)
        self.assertIn("UIComponents", actuator_config_props["required"])

    def test_ui_components_requires_request_and_response(self):
        """Test that UIComponents must have request and response objects."""
        actuator_config_props = WORKFLOW_SCHEMA["properties"]["actuator_config"]
        ui_components_props = actuator_config_props["properties"]["UIComponents"]

        self.assertIn("required", ui_components_props)
        self.assertIn("request", ui_components_props["required"])
        self.assertIn("response", ui_components_props["required"])

        # Both must be objects
        self.assertEqual(ui_components_props["properties"]["request"]["type"], "object")
        self.assertEqual(ui_components_props["properties"]["response"]["type"], "object")


class TestAdminFormPromptTemplateValidation(TestCase):
    """Tests that the Admin form blocks saving when prompt_template references are invalid."""

    def setUp(self):
        """Set up a temp directory with a valid base template."""
        self.tmpdir = tempfile.mkdtemp()
        self.temp_path = Path(self.tmpdir)

        base_template = self.temp_path / "base_valid.json"
        base_template.write_text('''{
            "schema_version": "1.0",
            "orchestrator_class": "DirectLLMResponse",
            "processor_config": {
                "LLMProcessor": {"provider": "default"}
            },
            "actuator_config": {
                "UIComponents": {
                    "request": {"component": "AIRequestComponent"},
                    "response": {"component": "AIResponseComponent"}
                }
            }
        }''')

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.tmpdir)

    def test_admin_form_rejects_nonexistent_prompt_template(self):
        """Test that the admin form raises ValidationError for nonexistent prompt_template."""
        from openedx_ai_extensions.admin import AIWorkflowProfileAdminForm  # pylint: disable=import-outside-toplevel

        form_data = {
            'slug': 'test-profile',
            'base_filepath': 'base_valid.json',
            'content_patch': '{"processor_config": {"LLMProcessor": {"prompt_template": "no-existe"}}}',
        }

        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            form = AIWorkflowProfileAdminForm(data=form_data)
            self.assertFalse(form.is_valid())
            # The error should mention the nonexistent prompt template
            all_errors = str(form.errors)
            self.assertIn("no-existe", all_errors)

    def test_admin_form_accepts_existing_prompt_template(self):
        """Test that the admin form accepts a valid prompt_template reference."""
        from openedx_ai_extensions.admin import AIWorkflowProfileAdminForm  # pylint: disable=import-outside-toplevel

        PromptTemplate.objects.create(slug="valid-admin-template", body="A real prompt.")

        form_data = {
            'slug': 'test-profile-valid',
            'base_filepath': 'base_valid.json',
            'content_patch': '{"processor_config": {"LLMProcessor": {"prompt_template": "valid-admin-template"}}}',
        }

        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            form = AIWorkflowProfileAdminForm(data=form_data)
            self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_admin_form_accepts_no_prompt_template(self):
        """Test that the admin form accepts config without prompt_template."""
        from openedx_ai_extensions.admin import AIWorkflowProfileAdminForm  # pylint: disable=import-outside-toplevel

        form_data = {
            'slug': 'test-profile-no-pt',
            'base_filepath': 'base_valid.json',
            'content_patch': '',
        }

        with override_settings(WORKFLOW_TEMPLATE_DIRS=[self.tmpdir]):
            form = AIWorkflowProfileAdminForm(data=form_data)
            self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
