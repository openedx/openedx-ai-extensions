from tutor import hooks
import os
from glob import glob

import importlib_resources
from tutormfe.hooks import PLUGIN_SLOTS
from .__about__ import __version__


@hooks.Filters.IMAGES_BUILD_MOUNTS.add()
def _mount_sample_plugin(mounts, path):
    """Mount the sample plugin source code for development."""
    mounts += [("openedx-ai-extensions/backend", "/openedx/openedx-ai-extensions/backend")]
    return mounts


for path in glob(str(importlib_resources.files("openedx_ai_extensions") / "patches" / "*")):
    with open(path, encoding="utf-8") as patch_file:
        hooks.Filters.ENV_PATCHES.add_item((os.path.basename(path), patch_file.read()))
