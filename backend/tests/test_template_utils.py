"""
Tests for openedx_ai_extensions.workflows.template_utils module.
"""
import shutil
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings

from openedx_ai_extensions.workflows.template_utils import (
    WORKFLOW_SCHEMA,
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

    def test_default_directory(self):
        """Test that default configs directory is returned when no settings."""
        # When WORKFLOW_TEMPLATE_DIRS is not set, should use default
        with override_settings(WORKFLOW_TEMPLATE_DIRS=None):
            dirs = get_template_directories()

            # Should return the default configs directory
            self.assertIsInstance(dirs, list)
            # The default directory might not exist in test environment
            # so we just check the function returns a list

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
        """Test validating a valid configuration."""
        config = {
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {"model": "gpt-4"},
            "actuator_config": {"UIComponents": {}}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertTrue(is_valid)
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
        # Should complain about missing processor_config and actuator_config
        self.assertGreater(len(errors), 0)

    def test_validate_empty_orchestrator_class(self):
        """Test that empty orchestrator_class is invalid."""
        config = {
            "orchestrator_class": "",
            "processor_config": {},
            "actuator_config": {}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("orchestrator_class" in err and "empty" in err for err in errors))

    def test_validate_invalid_orchestrator_class_identifier(self):
        """Test that invalid Python identifier is caught."""
        config = {
            "orchestrator_class": "Invalid-Class-Name!",
            "processor_config": {},
            "actuator_config": {}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("identifier" in err.lower() for err in errors))

    def test_validate_processor_config_not_dict(self):
        """Test that non-dict processor_config is invalid."""
        config = {
            "orchestrator_class": "TestOrchestrator",
            "processor_config": "not a dict",
            "actuator_config": {}
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("processor_config" in err for err in errors))

    def test_validate_actuator_config_not_dict(self):
        """Test that non-dict actuator_config is invalid."""
        config = {
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {},
            "actuator_config": ["not", "a", "dict"]
        }
        is_valid, errors = validate_workflow_config(config)

        self.assertFalse(is_valid)
        self.assertTrue(any("actuator_config" in err for err in errors))

    def test_validate_ui_components_not_dict(self):
        """Test that non-dict UIComponents is invalid."""
        config = {
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {},
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
            "orchestrator_class": "TestOrchestrator",
            "processor_config": {},
            "actuator_config": {},
            "custom_field": "custom_value",
            "schema_version": "1.0"
        }
        is_valid, _errors = validate_workflow_config(config)

        # Should be valid - additional properties are allowed
        self.assertTrue(is_valid)


class TestValidateSemantics(TestCase):
    """Tests for _validate_semantics function."""

    def test_valid_config_no_errors(self):
        """Test that valid config produces no errors."""
        config = {
            "orchestrator_class": "ValidOrchestrator",
            "processor_config": {},
            "actuator_config": {}
        }
        errors = _validate_semantics(config)

        self.assertEqual(len(errors), 0)

    def test_orchestrator_class_with_underscores(self):
        """Test that underscores in orchestrator_class are allowed."""
        config = {
            "orchestrator_class": "My_Test_Orchestrator",
            "processor_config": {},
            "actuator_config": {}
        }
        errors = _validate_semantics(config)

        self.assertEqual(len(errors), 0)

    def test_empty_orchestrator_class(self):
        """Test that empty orchestrator_class produces error."""
        config = {
            "orchestrator_class": "",
            "processor_config": {},
            "actuator_config": {}
        }
        errors = _validate_semantics(config)

        self.assertGreater(len(errors), 0)
        self.assertTrue(any("empty" in err for err in errors))

    def test_invalid_identifier_special_chars(self):
        """Test that special characters in orchestrator_class are rejected."""
        config = {
            "orchestrator_class": "Invalid@Orchestrator!",
            "processor_config": {},
            "actuator_config": {}
        }
        errors = _validate_semantics(config)

        self.assertGreater(len(errors), 0)


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


class TestWorkflowSchema(TestCase):
    """Tests for WORKFLOW_SCHEMA constant."""

    def test_schema_has_required_fields(self):
        """Test that schema defines required fields."""
        self.assertIn("required", WORKFLOW_SCHEMA)
        required = WORKFLOW_SCHEMA["required"]

        self.assertIn("orchestrator_class", required)
        self.assertIn("processor_config", required)
        self.assertIn("actuator_config", required)

    def test_schema_properties_defined(self):
        """Test that schema has property definitions."""
        self.assertIn("properties", WORKFLOW_SCHEMA)
        properties = WORKFLOW_SCHEMA["properties"]

        self.assertIn("orchestrator_class", properties)
        self.assertIn("processor_config", properties)
        self.assertIn("actuator_config", properties)
        self.assertIn("schema_version", properties)

    def test_schema_allows_additional_properties(self):
        """Test that schema allows additional properties."""
        self.assertTrue(WORKFLOW_SCHEMA.get("additionalProperties", False))
