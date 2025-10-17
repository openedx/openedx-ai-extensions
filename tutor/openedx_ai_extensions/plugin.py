from tutor import hooks
from tutormfe.hooks import PLUGIN_SLOTS

# Plugin metadata
__version__ = "1.0.0"

# Backend plugin installation
@hooks.Filters.IMAGES_BUILD_MOUNTS.add()
def _mount_sample_plugin(mounts):
    """Mount the sample plugin source code for development."""
    mounts.append(("openedx-ai-extensions/backend", "/openedx/openedx-ai-extensions/backend"))
    return mounts

hooks.Filters.IMAGES_BUILD.add_item(
    (
        "openedx",
        "RUN pip install openedx-ai-extensions==${OPENEDX_AI_EXTENSIONS_VERSION}",
        "openedx",
        (),
    )
)


hooks.Filters.ENV_PATCHES.add_item(
    (
        "mfe-dockerfile-post-npm-install",
        """
# npm package
RUN npm install @openedx/openedx-ai-extensions-ui
""",
    )
)


hooks.Filters.ENV_PATCHES.add_item(
    (
        "mfe-env-config-buildtime-imports",
        """
import { RedLine, GetAIAssistanceButton } from '@openedx/openedx-ai-extensions-ui';
""",
    )
)


PLUGIN_SLOTS.add_items([
    (
        "learning",
        "org.openedx.frontend.learning.unit_title.v1",
        """
        {
          op: PLUGIN_OPERATIONS.Insert,
          widget: {
             id: 'ai-red-line',
             type: DIRECT_PLUGIN,
             priority: 11,
             RenderWidget: RedLine,
           }
        },
        {
          op: PLUGIN_OPERATIONS.Insert,
          widget: {
             id: 'ai-assist',
             type: DIRECT_PLUGIN,
             priority: 10,
             RenderWidget: GetAIAssistanceButton,
           },
         }
        """
    ),
])
