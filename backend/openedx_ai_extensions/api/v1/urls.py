"""
Version 1 API URLs
"""
from django.urls import path
from .pipelines.views import AIGenericPipelinesView

app_name = 'v1'

urlpatterns = [
    path('pipelines/', AIGenericPipelinesView.as_view(), name='ai_pipelines'),
]
