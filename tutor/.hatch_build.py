"""
Build hook to read version from __about__.py
"""

import os

from hatchling.metadata.plugin.interface import MetadataHookInterface


class CustomMetadataHook(MetadataHookInterface):
    """
    Custom hook to read version from __about__.py
    """

    def update(self, metadata: dict) -> None:
        """
        Update the version metadata from __about__.py
        """
        here = os.path.dirname(__file__)
        about = {}
        with open(os.path.join(here, "openedx_ai_extensions", "__about__.py"), encoding="utf-8") as f:
            exec(f.read(), about)  # pylint: disable=exec-used
        metadata["version"] = about["__version__"]
