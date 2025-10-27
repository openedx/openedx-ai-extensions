import os
from glob import glob
from pathlib import Path

import importlib_resources
from tutor import hooks
from tutormfe.hooks import PLUGIN_SLOTS

hooks.Filters.CONFIG_DEFAULTS.add_items(
    [
        # Add your new settings that have default values here.
        # Each new setting is a pair: (setting_name, default_value).
        ("OPENEDX_AI_EXTENSIONS", [{
            "default": {
              "API_KEY": "put_your_api_key_here",
              "LITELLM_MODEL": "gpt-5-mini",
              "TEMPERATURE": 1,
            }
         }]),
    ]
)

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
def _mount_sample_plugin(mounts, path):
    """Mount the sample plugin source code for development."""
    mounts += [("openedx-ai-extensions-backend", "/openedx/openedx-ai-extensions/backend")]
    return mounts

# Actually connects the patch files as tutor env patches
for path in glob(str(importlib_resources.files("openedx_ai_extensions") / "patches" / "*")):
    with open(path, encoding="utf-8") as patch_file:
        hooks.Filters.ENV_PATCHES.add_item((os.path.basename(path), patch_file.read()))


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
                RenderWidget: GetAIAssistanceButton,
            },
          }""",
        ),
    ]
)
