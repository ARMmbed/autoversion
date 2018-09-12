import os
from setuptools import setup
from setuptools import find_packages

repository_dir = os.path.dirname(__file__)

# single source for project version information without side effects
__version__ = None
with open(os.path.join(repository_dir, "src", "auto_version", "__version__.py")) as fh:
    exec(fh.read())

setup(
    author="David Hyman",
    author_email="support@mbed.com",
    name="auto_version",
    long_description="Tool for managing SemVer versioning of a project.",
    license="Apache 2.0",
    version=__version__,
    include_package_data=True,
    package_dir={"": "src"},
    packages=find_packages("src"),
    install_requires=["toml"],
    entry_points=dict(
        console_scripts=[
            "auto_version = auto_version.auto_version_tool:main_from_cli",
            "auto-version = auto_version.auto_version_tool:main_from_cli",
        ]
    ),
)
