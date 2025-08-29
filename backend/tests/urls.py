"""
A URL Conf for testing.

We don't add the sample plugin URLs here because they should be added automatically by the plugin interface.
"""

from edx_django_utils.plugins import get_plugin_url_patterns

urlpatterns = []

urlpatterns.extend(get_plugin_url_patterns("lms.djangoapp"))
