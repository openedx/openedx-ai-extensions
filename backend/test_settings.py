"""
These settings are here to use during tests, because django requires them.

In a real-world use case, apps in this project are installed into other
Django applications, so these settings will not be used.
"""

from os.path import abspath, dirname, join

from edx_django_utils.plugins.plugin_apps import get_plugin_apps
from edx_django_utils.plugins.plugin_settings import add_plugins


def root(*args):
    """
    Get the absolute path of the given path relative to the project root.
    """
    return join(abspath(dirname(__file__)), *args)


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "default.db",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    }
}

# Plugin Settings
ENABLE_PLUGINS = True
# Define both contexts for reference, but we'll only use one for testing
PLUGIN_CONTEXTS = ["lms.djangoapp", "cms.djangoapp"]
# We only use the LMS context for testing as the plugin is configured similarly for both
# Could use CMS context instead by changing the index to 1

# Base INSTALLED_APPS before plugin discovery
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.sessions",
    "rest_framework",
    "django_filters",
    "edx_django_utils.plugins",
    "django_extensions",
    "eventtracking.django.apps.EventTrackingConfig",
    "submissions",
]

# Dynamically add plugin apps - only using the LMS context for simplicity
plugin_apps = get_plugin_apps(PLUGIN_CONTEXTS[0])
INSTALLED_APPS.extend(plugin_apps)

LOCALE_PATHS = [
    root("openedx_ai_extensions", "conf", "locale"),
]

ROOT_URLCONF = "tests.urls"

SECRET_KEY = "insecure-secret-key"

MIDDLEWARE = (
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": False,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",  # this is required for admin
                "django.template.context_processors.request",  # this is also required for admin navigation sidebar
                "django.contrib.messages.context_processors.messages",  # this is required for admin
            ],
        },
    }
]

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/hour",
        "user": "100/hour",
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
}

# AI Extensions configuration for tests
AI_EXTENSIONS = {
    "default": {
        "API_KEY": "test-api-key",
        "MODEL": "gpt-3.5-turbo",
        "TIMEOUT": 30,
        "TEMPERATURE": 0.7,
        "MAX_TOKENS": 1000,
    },
}

# Workflow template directories for tests
WORKFLOW_TEMPLATE_DIRS = [
    root("openedx_ai_extensions", "workflows", "profiles"),
]

# Event tracking configuration for tests (matches completion-aggregator pattern)
EVENT_TRACKING_ENABLED = True
EVENT_TRACKING_BACKENDS = {}
# Provided so the generated xAPI events use a known LMS URL when testing
LMS_ROOT_URL = "http://localhost:18000"
# Provided so the generated xAPI events use a known "event routing backends package string" when testing
RUNNING_WITH_TEST_SETTINGS = True

# Apply plugin settings - must be done after base settings are defined
# Only using the LMS context for simplicity
# Third parameter is the settings_type which should match the keys in settings_config
add_plugins(__name__, PLUGIN_CONTEXTS[0], "test")
