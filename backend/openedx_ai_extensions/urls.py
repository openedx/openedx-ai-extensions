"""
URLs for openedx_ai_extensions.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

# Create a router and register our viewsets with it
router = DefaultRouter()


# The API URLs are now determined automatically by the router
urlpatterns = [
    path("", include("openedx_ai_extensions.api.urls", namespace="api")),
]
