"""
Main API URLs for openedx-ai-extensions
"""
from django.urls import path, include

app_name = 'openedx_ai_extensions_api'

urlpatterns = [
    path('v1/', include('openedx_ai_extensions.api.v1.urls', namespace='v1')),
]
