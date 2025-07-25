"""
Common settings for the openedx_ai_extensions application.
"""


def plugin_settings(settings):
    """
    Add plugin settings to main settings object.

    Args:
        settings (dict): Django settings object
    """
    settings.AI_MODEL = 'gpt-4.1-mini'
    settings.OPENAI_API_KEY = "make_it_read_from_tutor"
