"""
Django admin configuration for AI Extensions models.
"""
import json
import logging

from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe

from openedx_ai_extensions.models import PromptTemplate
from openedx_ai_extensions.workflows.models import AIWorkflowProfile, AIWorkflowScope, AIWorkflowSession
from openedx_ai_extensions.workflows.template_utils import (
    discover_templates,
    get_effective_config,
    parse_json5_string,
    validate_workflow_config,
)


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    """
    Admin interface for Prompt Templates - one big textbox for easy editing.
    """

    list_display = ('slug', 'body_preview', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('slug', 'body')
    readonly_fields = ('id', 'created_at', 'updated_at')

    def get_fieldsets(self, request, obj=None):
        """Return dynamic fieldsets with UUID example if editing existing object."""
        if obj and obj.pk:
            # Editing existing - show UUID example
            identification_description = (
                f'Slug is human-readable, ID is the stable UUID reference.<br/>'
                f'Use in profile: <code>"prompt_template": "{obj.pk}"</code> or '
                f'<code>"prompt_template": "{obj.slug}"</code>'
            )
        else:
            # Creating new
            identification_description = (
                'Slug is human-readable, ID will be generated automatically.'
            )

        return (
            ('Identification', {
                'fields': ('slug', 'id'),
                'description': format_html(identification_description),
            }),
            ('Prompt Content', {
                'fields': ('body',),
                'description': 'The prompt template text - edit in the big textbox below.',
            }),
            ('Timestamps', {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',),
            }),
        )

    def get_form(self, request, obj=None, change=False, **kwargs):
        """Customize the form to use a large textarea for body."""
        form = super().get_form(request, obj, change=change, **kwargs)
        if 'body' in form.base_fields:
            form.base_fields['body'].widget = forms.Textarea(attrs={
                'rows': 25,
                'cols': 120,
                'class': 'vLargeTextField',
                'style': 'font-family: monospace; font-size: 14px;',
            })
        return form

    def body_preview(self, obj):
        """Show truncated body text."""
        if obj.body:
            preview = obj.body[:80].replace('\n', ' ')
            return preview + ('...' if len(obj.body) > 80 else '')
        return '-'

    body_preview.short_description = 'Prompt Preview'


class AIWorkflowProfileAdminForm(forms.ModelForm):
    """Custom form for AIWorkflowProfile with template selection."""

    class Meta:
        """Form metadata."""

        model = AIWorkflowProfile
        fields = '__all__'
        widgets = {
            'content_patch': forms.Textarea(attrs={
                'rows': 20,
                'cols': 80,
                'class': 'vLargeTextField',
                'style': 'font-family: monospace;',
            }),
        }

    def __init__(self, *args, **kwargs):
        """Initialize form with template choices and help text."""
        super().__init__(*args, **kwargs)

        # Populate base_filepath choices from discovered templates
        templates = discover_templates()
        if templates:
            self.fields['base_filepath'].widget = forms.Select(choices=templates)

        # Add help text for JSON5 editor
        self.fields['content_patch'].help_text = (
            'JSON5 Merge Patch (RFC 7386) to override base template values. '
            'Supports comments (//, /* */), trailing commas, and unquoted keys. '
            'Validation results appear in the "Preview & Validation" section below.'
        )

    def clean_content_patch(self):
        """Validate JSON5 syntax in content_patch."""
        content_patch_raw = self.cleaned_data.get('content_patch', '')

        # Empty is fine
        if not content_patch_raw or not content_patch_raw.strip():
            return ''

        # Validate JSON5 syntax
        try:
            parse_json5_string(content_patch_raw)
        except Exception as exc:
            raise ValidationError(f'Invalid JSON5 syntax: {exc}') from exc

        return content_patch_raw

    def clean(self):
        """Validate the effective configuration after merging base template with patch."""
        cleaned_data = super().clean()

        base_filepath = cleaned_data.get('base_filepath')
        content_patch_raw = cleaned_data.get('content_patch', '')

        if not base_filepath:
            return cleaned_data

        # Parse the content patch
        content_patch = {}
        if content_patch_raw and content_patch_raw.strip():
            try:
                content_patch = parse_json5_string(content_patch_raw)
            except Exception:  # pylint: disable=broad-exception-caught
                # Already caught in clean_content_patch
                return cleaned_data

        # Get effective config and validate it
        effective_config = get_effective_config(base_filepath, content_patch)
        if effective_config is None:
            return cleaned_data

        is_valid, errors = validate_workflow_config(effective_config)
        if not is_valid:
            raise ValidationError(
                'Effective configuration is invalid: %(errors)s',
                params={'errors': '; '.join(errors)},
            )

        return cleaned_data


@admin.register(AIWorkflowProfile)
class AIWorkflowProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for AI Workflow Profiles with preview and validation.
    """

    form = AIWorkflowProfileAdminForm

    list_display = ('slug', 'base_filepath', 'description_preview', 'is_valid')
    list_filter = ('base_filepath',)
    search_fields = ('slug', 'description', 'base_filepath')

    fieldsets = (
        ('Basic Information', {
            'fields': ('slug', 'description'),
        }),
        ('Profile Template Configuration', {
            'fields': ('base_filepath', 'base_template_preview', 'content_patch'),
            'description': 'Select a base template and optionally override values with JSON patch.'
        }),
        ('Preview & Validation', {
            'fields': ('effective_config_preview', 'validation_status'),
            'classes': ('collapse',),
            'description': 'View the merged configuration and validation results.'
        }),
    )

    readonly_fields = ('base_template_preview', 'effective_config_preview', 'validation_status')

    def description_preview(self, obj):
        """Show truncated description."""
        if obj.description:
            return obj.description[:50] + ('...' if len(obj.description) > 50 else '')
        return '-'
    description_preview.short_description = 'Description'

    def is_valid(self, obj):
        """Show validation status with icon."""
        is_valid, errors = obj.validate()
        if is_valid:
            return format_html('<span class="ai-admin-preview--success">✓ Valid</span>')
        return format_html(
            '<span class="ai-admin-preview--error">✗ {} errors</span>',
            len(errors),
        )
    is_valid.short_description = 'Status'

    def base_template_preview(self, obj):
        """Show the base template file content as-is."""
        if not obj.base_filepath:
            return '-'

        from openedx_ai_extensions.workflows.template_utils import (  # pylint: disable=import-outside-toplevel
            get_template_directories,
            is_safe_template_path,
        )

        if not is_safe_template_path(obj.base_filepath):
            return format_html(
                '<div class="ai-admin-preview ai-admin-preview--error">'
                '<strong>Error:</strong> Invalid or unsafe template path'
                '</div>'
            )

        file_content = None
        for base_dir in get_template_directories():
            full_path = base_dir / obj.base_filepath
            if full_path.exists():
                file_content = full_path.read_text(encoding='utf-8')
                break

        if file_content is None:
            return format_html(
                '<div class="ai-admin-preview ai-admin-preview--error">'
                '<strong>Error:</strong> Template file not found'
                '</div>'
            )

        preview_id = f'base-template-{obj.pk or "new"}'

        return format_html(
            '<a href="#" class="ai-admin-toggle" '
            'onclick="var el=document.getElementById(\'{id}\');'
            'el.style.display = el.style.display === \'none\' ? \'block\' : \'none\';'
            'return false;">'
            '▶ Toggle Base Template ({path})</a>'
            '<div id="{id}" class="ai-admin-preview" style="display:none;">'
            '<pre>{content}</pre>'
            '</div>',
            id=preview_id,
            path=obj.base_filepath,
            content=escape(file_content),
        )
    base_template_preview.short_description = 'Base Template (Read-Only)'

    def effective_config_preview(self, obj):
        """Show the effective merged configuration as formatted JSON."""
        if obj.pk is None:
            return '-'

        try:
            formatted = json.dumps(obj.config, indent=2, sort_keys=True)
            return format_html(
                '<div class="ai-admin-preview">'
                '<strong>Effective Configuration:</strong>'
                '<pre>{}</pre>'
                '</div>',
                formatted,
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return format_html(
                '<div class="ai-admin-preview ai-admin-preview--error">'
                '<strong>Error:</strong> {}'
                '</div>',
                exc,
            )
    effective_config_preview.short_description = 'Effective Configuration'

    def validation_status(self, obj):
        """Show detailed validation results."""
        if obj.pk is None:
            return '-'

        is_valid, errors = obj.validate()

        if is_valid:
            return format_html(
                '<div class="ai-admin-preview ai-admin-preview--success">'
                '✓ Configuration is valid'
                '</div>'
            )

        error_list = '<br>'.join(f'• {escape(e)}' for e in errors)
        return format_html(
            '<div class="ai-admin-preview ai-admin-preview--error">'
            '<strong>Validation errors:</strong><br>{}'
            '</div>',
            mark_safe(error_list),
        )
    validation_status.short_description = 'Validation Status'

    class Media:
        """Admin media assets."""

        css = {
            'all': ('openedx_ai_extensions/admin.css',),
        }


@admin.register(AIWorkflowSession)
class AIWorkflowSessionAdmin(admin.ModelAdmin):
    """
    Admin interface for managing AI Workflow Sessions.
    """

    list_display = ("user", "course_id", "location_id")
    search_fields = ("user__username", "course_id", "location_id")
    readonly_fields = ("local_submission_id", "remote_response_id", "metadata")
    actions = ["debug_thread"]

    def get_urls(self):
        custom_urls = [
            path(
                "debug-thread/",
                self.admin_site.admin_view(self.debug_thread_view),
                name="aiworkflowsession_debug_thread",
            ),
        ]
        return custom_urls + super().get_urls()

    @admin.action(description="Debug thread")
    def debug_thread(self, request, queryset):
        """Redirect selected sessions to the debug thread view."""
        ids = ",".join(str(s.id) for s in queryset)
        from django.shortcuts import redirect  # pylint: disable=import-outside-toplevel
        return redirect(f"debug-thread/?ids={ids}")

    def debug_thread_view(self, request):
        """Render the full local and remote threads for selected sessions."""
        if not (
            self.has_view_permission(request)
            and request.user.has_perm("submissions.view_submission")
        ):
            raise PermissionDenied

        _logger = logging.getLogger(__name__)

        ids = request.GET.get("ids", "").split(",")
        ids = [i.strip() for i in ids if i.strip()]

        sessions = AIWorkflowSession.objects.filter(id__in=ids).select_related("user", "scope", "profile")

        results = []
        for session in sessions:
            session_data = {
                "session_id": str(session.id),
                "user": session.user.username,
                "course_id": str(session.course_id) if session.course_id else None,
                "location_id": str(session.location_id) if session.location_id else None,
                "profile": session.profile.slug if session.profile else None,
                "local_submission_id": session.local_submission_id,
                "remote_response_id": session.remote_response_id,
                "local_thread": None,
                "remote_thread": None,
                "combined_thread": None,
                "local_thread_error": None,
                "remote_thread_error": None,
                "combined_thread_error": None,
            }

            try:
                session_data["local_thread"] = session.get_local_thread()
            except Exception as e:  # pylint: disable=broad-exception-caught
                _logger.exception("Error fetching local thread for session %s", session.id)
                session_data["local_thread_error"] = str(e)

            try:
                session_data["remote_thread"] = session.get_remote_thread()
            except Exception as e:  # pylint: disable=broad-exception-caught
                _logger.exception("Error fetching remote thread for session %s", session.id)
                session_data["remote_thread_error"] = str(e)

            try:
                session_data["combined_thread"] = session.get_combined_thread()
            except Exception as e:  # pylint: disable=broad-exception-caught
                _logger.exception("Error building combined thread for session %s", session.id)
                session_data["combined_thread_error"] = str(e)

            results.append(session_data)

        # JSON response if requested
        if request.GET.get("format") == "json":
            return JsonResponse({"sessions": results}, json_dumps_params={"indent": 2})

        session_ids = [r["session_id"] for r in results]
        context = {
            **self.admin_site.each_context(request),
            "title": "Debug Thread",
            "results": results,
            "results_json": json.dumps(results, indent=2, default=str),
            "session_ids_json": json.dumps(session_ids),
        }
        return TemplateResponse(request, "admin/debug_thread.html", context)


@admin.register(AIWorkflowScope)
class AIWorkflowConfigAdmin(admin.ModelAdmin):
    """
    Admin interface for managing AI Workflow Configurations.
    """

    list_display = (
        "course_id",
        "location_regex",
        "service_variant",
        "profile",
        "enabled",
    )
    search_fields = ("course_id", "location_regex", "profile__slug")
    list_filter = ("service_variant", "enabled")
