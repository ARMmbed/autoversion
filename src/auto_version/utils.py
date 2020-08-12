"""Functions for manipulating SemVer objects (Major.Minor.Patch)"""
import logging

import semver
from auto_version.config import AutoVersionConfig as config
from auto_version.config import Constants
from auto_version.definitions import SemVerSigFig

_LOG = logging.getLogger(__file__)


def from_text_or_none(text):
    """A version or None

    :rtype: semver.VersionInfo | None
    """
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
    return semver.parse_version_info(result)


def get_token_args(sig_fig):
    token_args = {}
    if sig_fig == SemVerSigFig.build:
        token_args = {"token": config.BUILD_TOKEN}
    if sig_fig == SemVerSigFig.prerelease:
        token_args = {"token": config.PRERELEASE_TOKEN}
    return token_args


def max_sigfig(sigfigs):
    """Given a list of significant figures, return the largest"""
    for sig_fig in SemVerSigFig:  # iterate sig figs in order of significance
        if sig_fig in sigfigs:
            return sig_fig


def min_sigfig(sigfigs):
    """Given a list of significant figures, return the smallest"""
    for sig_fig in reversed(SemVerSigFig):  # iterate sig figs in order of least significance
        if sig_fig in sigfigs:
            return sig_fig


def semver_diff(semver1, semver2):
    """Given some semvers, return the largest difference between them"""
    for sig_fig in SemVerSigFig:
        if getattr(semver1, sig_fig) != getattr(semver2, sig_fig):
            return sig_fig


def sigfig_gt(sig_fig1, sig_fig2):
    """Returns True if sf1 > sf2"""
    return SemVerSigFig.index(sig_fig1) < SemVerSigFig.index(sig_fig2)


def sigfig_lt(sig_fig1, sig_fig2):
    """Returns True if sf1 < sf2"""
    return SemVerSigFig.index(sig_fig1) > SemVerSigFig.index(sig_fig2)


def is_release(semver):
    """is a semver a release version"""
    return not (semver.build or semver.prerelease)


def make_new_semver(current_semver, last_release_semver, all_triggers, **overrides):
    """Defines how to increment semver based on which significant figure is triggered

    :param current_semver: the version to increment
    :param last_release_semver: the previous release version, if available
    :param all_triggers: list of major/minor/patch/prerelease
    :param overrides: explicit values for some or all of the sigfigs
    :return:
    """
    version_string = str(current_semver)

    # if the current version isn't a full release
    if not is_release(current_semver) and last_release_semver:
        # we check to see how important the changes are
        # in the triggers, compared to the changes made between the current version and previous release
        if sigfig_gt(max_sigfig(all_triggers), semver_diff(current_semver, last_release_semver)):
            # here, the changes are more significant than the original RC bump, so we re-bump
            pass
        else:
            # here the changes are same or lesser than the original RC bump, so we only bump prerelease
            all_triggers = {SemVerSigFig.prerelease}

    if is_release(current_semver):
        # if the current semver is a release, we can't just do a prerelease or build increment
        # there *must* be a minimum patch increment, otherwise you could get 2.0.0 -> 2.0.0-RC.1
        all_triggers.add(SemVerSigFig.patch)

    bump_sigfig = max_sigfig(all_triggers)

    if bump_sigfig:
        # perform an increment using the most-significant trigger
        version_string = getattr(semver, "bump_" + bump_sigfig)(
            str(current_semver), **get_token_args(bump_sigfig)
        )

        if sigfig_gt(bump_sigfig, SemVerSigFig.prerelease):
            # if we *didnt* increment sub-patch already, then we should do so
            # this provides the "devmode template" as previously
            # and ensures a simple 'bump' doesn't look like a full release
            version_string = semver.bump_prerelease(
                version_string, token=config.PRERELEASE_TOKEN
            )

    # perform any explicit setting of sigfigs
    version_info = semver.parse_version_info(version_string)
    for k, v in overrides.items():
        token_args = get_token_args(k)
        prefix = list(token_args.values()).pop() + "." if token_args else ""
        setattr(version_info, "_" + k, prefix + str(v))

    return version_info
