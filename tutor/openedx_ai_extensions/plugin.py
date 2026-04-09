import os
from glob import glob
from pathlib import Path

import importlib_resources
from tutor import hooks
from tutormfe.hooks import PLUGIN_SLOTS


########################
# Plugin path management
########################

PLUGIN_DIR = Path(__file__).parent

# Locate backend and frontend directories
# They should be siblings to the openedx_ai_extensions package
PACKAGE_ROOT = PLUGIN_DIR.parent
FRONTEND_CANDIDATES = [
    PACKAGE_ROOT / "openedx-ai-extensions-frontend",
    PACKAGE_ROOT.parent / "frontend",
]
FRONTEND_PATH = next((p for p in FRONTEND_CANDIDATES if p.exists()), None)
BACKEND_CANDIDATES = [
    PACKAGE_ROOT / "openedx-ai-extensions-backend",
    PACKAGE_ROOT.parent / "backend",
]
BACKEND_PATH = next((p for p in BACKEND_CANDIDATES if p.exists()), None)

# Makes the UI Slots code available for local install during the build process
hooks.Filters.DOCKER_BUILD_COMMAND.add_items([
    "--build-context", f"ai-extensions-frontend={str(FRONTEND_PATH)}",
    "--build-context", f"ai-extensions-backend={str(BACKEND_PATH)}",
])

@hooks.Filters.IMAGES_BUILD_MOUNTS.add()
def _mount_plugin(mounts, path):
    """Mount the sample plugin source code for development."""
    mounts += [("openedx-ai-extensions-backend", "/openedx/openedx-ai-extensions/backend")]
    return mounts

########################
# Configuration defaults
########################

hooks.Filters.CONFIG_DEFAULTS.add_items([
    ("AI_EXTENSIONS_ENABLE_LLM_CACHE", False),
    ("AI_EXTENSIONS_LLM_CACHE", {}),
    ("AI_EXTENSIONS_ENABLE_EVENT_BUS_CONSUMER", False),
])

# Actually connects the patch files as tutor env patches
for path in glob(str(importlib_resources.files("openedx_ai_extensions") / "patches" / "*")):
    with open(path, encoding="utf-8") as patch_file:
        hooks.Filters.ENV_PATCHES.add_item((os.path.basename(path), patch_file.read()))


########################
# Template rendering
# Required for superset-extra-assets (datasets, charts, dashboards)
########################

hooks.Filters.ENV_TEMPLATE_ROOTS.add_items(
    [
        str(importlib_resources.files("openedx_ai_extensions") / "templates"),
    ]
)

hooks.Filters.ENV_TEMPLATE_TARGETS.add_items(
    [
        ("openedx-ai-extensions/build", "plugins"),
        ("openedx-ai-extensions/build/assets", "plugins"),
    ],
)


########################
# UI Slot configurations
########################

PLUGIN_SLOTS.add_items(
    [
        (
            "learning",
            "org.openedx.frontend.learning.unit_title.v1",
            """
          {
            op: PLUGIN_OPERATIONS.Insert,
            widget: {
                id: 'ai-assist-button',
                priority: 10,
                type: DIRECT_PLUGIN,
                RenderWidget: ConfigurableAIAssistance,
            },
          }""",
        ),
        (
            "authoring",
            "org.openedx.frontend.authoring.course_unit_sidebar.v2",
            """
          {
            op: PLUGIN_OPERATIONS.Insert,
            widget: {
                id: 'ai-assist-button-course-outline-sidebar',
                priority: 60,
                type: DIRECT_PLUGIN,
                RenderWidget: ConfigurableAIAssistance,
            },
          }""",
        ),
        (
            "authoring",
            "org.openedx.frontend.authoring.additional_course_plugin.v1",
            """
            {
                op: PLUGIN_OPERATIONS.Insert,
                widget: {
                    id: 'ai-extensions-settings-card',
                    type: DIRECT_PLUGIN,
                    RenderWidget: AIExtensionsCard
                },
            }"""
        )
    ]
)
