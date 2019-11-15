"""Functions for manipulating SemVer objects (Major.Minor.Patch)"""
import logging

import semver
from auto_version.config import AutoVersionConfig as config
from auto_version.config import Constants
from auto_version.definitions import SemVerSigFig

_LOG = logging.getLogger(__file__)


def from_text_or_none(text):
    """A version or None"""
    if text is not None:
        try:
            return semver.parse_version_info(text)
        except ValueError:
            _LOG.debug("version string is not semver-compatible: %r", text)
            pass


def get_semver_from_source(data):
    """Given a dictionary of all version data available, determine the current version"""
    # get the not-none values from data
    known = {
        key: data.get(alias)
        for key, alias in config._forward_aliases.items()
        if data.get(alias) is not None
    }
    _LOG.debug("valid, mapped keys: %r", known)

    # prefer the non-strict field, if available, because it retains more information
    potentials = [
        known.get(Constants.VERSION_FIELD, None),
        known.get(Constants.VERSION_STRICT_FIELD, None),
    ]

    # build from components, if they're defined
    from_components = {k: known.get(k) for k in SemVerSigFig if k in known}
    try:
        potentials.append(str(semver.VersionInfo(**from_components)))
    except TypeError:
        # we didn't have enough components
        pass

    versions = [potential for potential in potentials if from_text_or_none(potential)]
    release_versions = {semver.finalize_version(version) for version in versions}

    if len(release_versions) > 1:
        raise ValueError(
            "conflicting versions within project: %s\nkeys were: %r"
            % (release_versions, known)
        )

    if not versions:
        _LOG.debug("key pairs found: \n%r", known)
        raise ValueError("could not find existing semver")

    result = None
    if versions:
        result = versions[0]
    _LOG.info("latest version found in source: %r", result)
    return result


def get_token_args(sig_fig):
    token_args = {}
    if sig_fig == SemVerSigFig.build:
        token_args = {"token": config.BUILD_TOKEN}
    if sig_fig == SemVerSigFig.prerelease:
        token_args = {"token": config.PRERELEASE_TOKEN}
    return token_args


def make_new_semver(version_string, all_triggers, **overrides):
    """Defines how to increment semver based on which significant figure is triggered
    (most significant takes precendence)

    :param version_string: the version to increment
    :param all_triggers: major/minor/patch/prerelease
    :param overrides: explicit values for some or all of the sigfigs
    :return:
    """

    # perform an increment using the most-significant trigger
    also_prerelease = True
    for sig_fig in SemVerSigFig:  # iterate sig figs in order of significance
        if sig_fig in all_triggers:
            if sig_fig in (SemVerSigFig.prerelease, SemVerSigFig.build):
                also_prerelease = False
            version_string = getattr(semver, "bump_" + sig_fig)(
                version_string, **get_token_args(sig_fig)
            )
            break

    if also_prerelease:
        # if we *didnt* increment sub-patch, then we should do so
        # this provides the "devmode template" as previously
        # and ensures a simple 'bump' doesn't look like a full release
        version_string = semver.bump_prerelease(
            version_string, token=config.PRERELEASE_TOKEN
        )

    # perform any explicit setting of parts
    version_info = semver.parse_version_info(version_string)
    for k, v in overrides.items():
        token_args = get_token_args(k)
        prefix = list(token_args.values()).pop() + "." if token_args else ""
        setattr(version_info, "_" + k, prefix + str(v))
    version_string = str(version_info)

    return version_string
