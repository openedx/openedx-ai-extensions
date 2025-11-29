"""
Test fixtures for mocking the 'submissions' package.

Some parts of Open edX import `submissions.models` or `submissions.api`, but the
submissions Django app is not installed in unit test mode. We create a lightweight
fake package structure here so imports succeed without requiring the full app.
"""

import sys
from types import ModuleType

# Create fake root package
fake_submissions = ModuleType("submissions")

# Create fake submodules
fake_models = ModuleType("submissions.models")
fake_api = ModuleType("submissions.api")

# Attach submodules as attributes so static analysis tools see them
fake_submissions.models = fake_models
fake_submissions.api = fake_api

# Register modules in sys.modules so Python import machinery finds them
sys.modules["submissions"] = fake_submissions
sys.modules["submissions.models"] = fake_models
sys.modules["submissions.api"] = fake_api
