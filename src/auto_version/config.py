"""Configuration system for the auto_version tool"""
import logging
import os

import toml
from auto_version.definitions import SemVerSigFig

_LOG = logging.getLogger(__name__)


class Constants(object):
    """Internal - reused strings"""

    # regex groups
    KEY_GROUP = "KEY"
    VALUE_GROUP = "VALUE"

    # internal field keys
    VERSION_FIELD = "VERSION_KEY"
    VERSION_STRICT_FIELD = "VERSION_KEY_STRICT"
    VERSION_LOCK_FIELD = "VERSION_LOCK"
    RELEASE_FIELD = "RELEASE_FIELD"
    COMMIT_COUNT_FIELD = "COMMIT_COUNT"
    COMMIT_FIELD = "COMMIT"

    # source and destination control
    FROM_SOURCE = "source"
    FROM_VCS_PREVIOUS_VERSION = "vcs-prev-version"
    FROM_VCS_PREVIOUS_RELEASE = "vcs-prev-release"
    FROM_VCS_LATEST_VERSION = "vcs-global-version"
    FROM_VCS_LATEST_RELEASE = "vcs-global-release"
    TO_SOURCE = "source"
    TO_VCS = "vcs"

    # as used in toml file
    CONFIG_KEY = "AutoVersionConfig"


class AutoVersionConfig(object):
    """Configuration - can be overridden using a toml config file"""

    CONFIG_NAME = "DEFAULT"
    RELEASED_VALUE = True
    VERSION_LOCK_VALUE = True
    VERSION_UNLOCK_VALUE = False
    key_aliases = {
        "__version__": Constants.VERSION_FIELD,
        "__strict_version__": Constants.VERSION_STRICT_FIELD,
        "PRODUCTION": Constants.RELEASE_FIELD,
        "MAJOR": SemVerSigFig.major,
        "MINOR": SemVerSigFig.minor,
        "PATCH": SemVerSigFig.patch,
        "VERSION_LOCK": Constants.VERSION_LOCK_FIELD,
        Constants.COMMIT_COUNT_FIELD: Constants.COMMIT_COUNT_FIELD,
        Constants.COMMIT_FIELD: Constants.COMMIT_FIELD,
    }
    _forward_aliases = {}  # autopopulated later - reverse mapping of the above
    targets = [os.path.join("src", "_version.py")]
    regexers = {
        ".json": r"""^\s*[\"]?(?P<KEY>[\w:]+)[\"]?\s*:[\t ]*[\"']?(?P<VALUE>((\\\")?[^\r\n\t\f\v\",](\\\")?)+)[\"']?,?""",  # noqa
        ".yaml": r"""^\s*[\"']?(?P<KEY>[\w]+)[\"']?\s*:\s*[\"']?(?P<VALUE>[\w\-.+\\\/:]*[^'\",\[\]#\s]).*""",  # noqa
        ".yml": r"""^\s*[\"']?(?P<KEY>[\w]+)[\"']?\s*:\s*[\"']?(?P<VALUE>[\w\-.+\\\/:]*[^'\",\[\]#\s]).*""",  # noqa
        ".py": r"""^\s*['\"]?(?P<KEY>\w+)['\"]?\s*[=:]\s*['\"]?(?P<VALUE>[^\r\n\t\f\v\"']+)['\"]?,?""",  # noqa
        ".cs": r"""^(\w*\s+)*(?P<KEY>\w+)\s?[=:]\s*['\"]?(?P<VALUE>[^\r\n\t\f\v\"']+)['\"].*""",  # noqa
        ".csproj": r"""^<(?P<KEY>\w+)>(?P<VALUE>\S+)<\/\w+>""",  # noqa
        ".properties": r"""^\s*(?P<KEY>\w+)\s*=[\t ]*(?P<VALUE>[^\r\n\t\f\v\"']+)?""",  # noqa
    }
    trigger_patterns = {
        os.path.join("docs", "news", "*.major"): SemVerSigFig.major,
        os.path.join("docs", "news", "*.feature"): SemVerSigFig.minor,
        os.path.join("docs", "news", "*.bugfix"): SemVerSigFig.patch,
    }
    PRERELEASE_TOKEN = "pre"
    BUILD_TOKEN = "build"
    TAG_TEMPLATE = "release/{version}"
    MIN_NONE_RELEASE_SIGFIG = (
        "prerelease"
    )  # the minimum significant figure to increment is this isn't a release

    @classmethod
    def _deflate(cls):
        """Prepare for serialisation - returns a dictionary"""
        data = {k: v for k, v in vars(cls).items() if not k.startswith("_")}
        return {Constants.CONFIG_KEY: data}

    @classmethod
    def _inflate(cls, data):
        """Update config by deserialising input dictionary"""
        for k, v in data[Constants.CONFIG_KEY].items():
            setattr(cls, k, v)
        return cls._deflate()


def get_or_create_config(path, config):
    """Using TOML format, load config from given path, or write out example based on defaults"""
    if os.path.isfile(path):
        with open(path) as fh:
            _LOG.debug("loading config from %s", os.path.abspath(path))
            config._inflate(toml.load(fh))
    else:
        try:
            os.makedirs(os.path.dirname(path))
        except OSError:
            pass
        with open(path, "w") as fh:
            toml.dump(config._deflate(), fh)
