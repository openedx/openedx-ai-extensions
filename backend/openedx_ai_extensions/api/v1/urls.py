"""
Version 1 API URLs
"""

from django.urls import path

from .workflows.views import AIGenericWorkflowView, AIWorkflowProfilesListView, AIWorkflowProfileView

app_name = "v1"

urlpatterns = [
    path("workflows/", AIGenericWorkflowView.as_view(), name="aiext_workflows"),
    path("profile/", AIWorkflowProfileView.as_view(), name="aiext_ui_config"),
    path("profiles/", AIWorkflowProfilesListView.as_view(), name="aiext_profiles_list"),
]
