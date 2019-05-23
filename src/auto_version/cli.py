"""Load cli options"""
import argparse
import os

from auto_version import __version__
from auto_version.config import Constants
from auto_version.definitions import SemVerSigFig


def get_cli():
    """Load cli options"""
    parser = argparse.ArgumentParser(
        prog="auto_version",
        description="auto version v%s: a tool to control version numbers" % __version__,
    )
    parser.add_argument(
        "--show",
        "--dry-run",
        action="store_true",
        help="Don't write anything to disk or vcs.",
    )
    parser.add_argument(
        "--bump",
        choices=SemVerSigFig,
        help="Bumps the specified part of SemVer string. "
        "Use this locally to correctly modify the version file.",
    )
    parser.add_argument(
        "--news",
        "--file-triggers",
        action="store_true",
        dest="file_triggers",
        help="Detects need to bump based on presence of files (as specified in config).",
    )
    parser.add_argument(
        "--incr-from-release",
        action="store_true",
        help="Automatically sets version number based on SCIENCE (see docs). Requires use of VCS tags.",
    )
    parser.add_argument(
        "--print-file-triggers",
        action="store_true",
        help="Prints a newline separated list of files detected as bump triggers.",
    )
    parser.add_argument(
        "--set",
        help="Set the SemVer string. Use this locally to set the project version explicitly.",
    )
    parser.add_argument(
        "--commit-count-as",
        choices=SemVerSigFig,
        help="Use the commit count to set the value of the specified field.",
    )
    parser.add_argument(
        "--lock",
        action="store_true",
        help="Locks the SemVer string. "
        "Lock will remain for another call to autoversion before being cleared.",
    )
    parser.add_argument(
        "--release",
        action="store_true",
        default=False,
        help="Marks as a release build, which flags the build as released.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        default=False,
        help="Prints the version of auto_version itself (self-version).",
    )
    parser.add_argument(
        "--persist-from",
        choices={
            Constants.FROM_SOURCE,
            Constants.FROM_VCS_PREVIOUS_VERSION,
            Constants.FROM_VCS_PREVIOUS_RELEASE,
            Constants.FROM_VCS_LATEST_VERSION,
            Constants.FROM_VCS_LATEST_RELEASE,
        },
        action="append",
        default=[],
        help="Where the current version is stored. Looks for each source in order. (default: source files)",
    )
    parser.add_argument(
        "--persist-to",
        action="append",
        choices={Constants.TO_SOURCE, Constants.TO_VCS},
        default=[],
        help="Where the new version is stored. This could be in multiple places at once. (default: source files)",
    )
    default_config_file_path = os.path.join(os.getcwd(), "pyproject.toml")
    parser.add_argument(
        "--config",
        help="Configuration file path. (default: %s)." % default_config_file_path,
        default=default_config_file_path,
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        action="count",
        default=0,
        help="increase output verbosity. " "can be specified multiple times",
    )
    return parser.parse_known_args()
