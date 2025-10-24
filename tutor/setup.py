from setuptools import setup

setup(
    name="openedx-ai-extensions",
    version="0.1.0",
    packages=["openedx_ai_extensions"],
    entry_points={
        "tutor.plugin.v1": [
            "openedx-ai-extensions = openedx_ai_extensions.plugin"
        ]
    },
)
