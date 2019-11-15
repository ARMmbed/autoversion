# flake8: noqa
"""Generates DVCS version information

see also:
https://git-scm.com/docs/git-shortlog
https://www.python.org/dev/peps/pep-0440/
https://pypi.python.org/pypi/semver
https://pypi.python.org/pypi/bumpversion
https://github.com/warner/python-versioneer
https://pypi.org/project/autoversion/
https://pypi.org/project/auto-version/
https://github.com/javrasya/version-manager

"""
import ast
import glob
import logging
import os
import pprint
import re
import shlex
import subprocess
import warnings

import semver
from auto_version import __version__
from auto_version import definitions
from auto_version import utils
from auto_version.cli import get_cli
from auto_version.config import AutoVersionConfig as config
from auto_version.config import Constants
from auto_version.config import get_or_create_config
from auto_version.replacement_handler import ReplacementHandler

_LOG = logging.getLogger(__file__)


def replace_lines(regexer, handler, lines):
    """Uses replacement handler to perform replacements on lines of text

    First we strip off all whitespace
    We run the replacement on a clean 'content' string
    Finally we replace the original content with the replaced version
    This ensures that we retain the correct whitespace from the original line
    """
    result = []
    for line in lines:
        content = line.strip()
        replaced = regexer.sub(handler, content)
        result.append(line.replace(content, replaced, 1))
    return result


def write_targets(targets, **params):
    """Writes version info into version file"""
    handler = ReplacementHandler(**params)
    for target, regexer in regexer_for_targets(targets):
        with open(target) as fh:
            lines = fh.readlines()
        lines = replace_lines(regexer, handler, lines)
        with open(target, "w") as fh:
            fh.writelines(lines)
    if handler.missing:
        raise Exception(
            "Failed to complete all expected replacements: %r" % handler.missing
        )


def regexer_for_targets(targets):
    """Pairs up target files with their correct regex"""
    for target in targets:
        path, file_ext = os.path.splitext(target)
        regexer = config.regexers[file_ext]
        yield target, regexer


def extract_keypairs(lines, regexer):
    """Given some lines of text, extract key-value pairs from them"""
    updates = {}
    for line in lines:
        # for consistency we must match the replacer and strip whitespace / newlines
        match = regexer.match(line.strip())
        if not match:
            continue
        k_v = match.groupdict()
        updates[k_v[Constants.KEY_GROUP]] = k_v[Constants.VALUE_GROUP]
    return updates


def read_targets(targets):
    """Reads generic key-value pairs from input files"""
    results = {}
    for target, regexer in regexer_for_targets(targets):
        with open(target) as fh:
            results.update(extract_keypairs(fh.readlines(), regexer))
    _LOG.debug("found the following key-value pairs in source: %r", results)
    return results


def detect_file_triggers(release_commit):
    """The existence of files matching configured globs will trigger a version bump"""
    all_valid_trigger_files = set()
    triggers = set()
    for trigger, pattern in config.trigger_patterns.items():
        matches = glob.glob(pattern)

        if matches:
            valid_news = set(matches)
            if release_commit:
                # if we have a specific release commit, we will additionally filter
                # to ensure that only files that were added since that commit are considered
                # this allows the project to retain newsfiles for all time, rather than having to delete them

                # fortunately, git filter syntax is compatible with the glob syntax we're already using
                git_response = (
                    subprocess.check_output(
                        [
                            "git",
                            "diff",
                            "--relative",
                            "--name-status",
                            release_commit,
                            "HEAD",
                            "--diff-filter",
                            "A",
                            pattern,
                        ]
                    )
                    .decode("utf8")
                    .strip()
                    .splitlines()
                )
                file_paths = [path.split()[1].strip() for path in git_response]
                _LOG.debug("trigger: added since last release: %r", file_paths)
                valid_news.intersection_update(set(file_paths))

            # perform the additional filtering
            if valid_news:
                _LOG.debug(
                    "trigger: %s bump from %r\n\t%s", trigger, pattern, valid_news
                )
                triggers.add(trigger)
                all_valid_trigger_files.update(valid_news)
            else:
                _LOG.debug(
                    "trigger: no match on %r because files aren't new: %s",
                    pattern,
                    matches,
                )
        else:
            _LOG.debug("trigger: no match on %r", pattern)
    return triggers, all_valid_trigger_files


def get_all_triggers(bump, enable_file_triggers, release_commit):
    """Aggregated set of significant figures to bump"""
    triggers = set()
    if enable_file_triggers:
        file_triggers, _ = detect_file_triggers(release_commit)
        triggers.update(file_triggers)
    if bump:
        _LOG.debug("trigger: %s bump requested", bump)
        _ = definitions.SemVerSigFig._asdict()[bump]
        triggers.add(bump)
    return triggers


def get_lock_behaviour(triggers, all_data, lock):
    """Binary state lock protects from version increments if set"""
    updates = {}
    lock_key = config._forward_aliases.get(Constants.VERSION_LOCK_FIELD)
    # if we are explicitly setting or locking the version, then set the lock field True anyway
    if lock:
        updates[Constants.VERSION_LOCK_FIELD] = config.VERSION_LOCK_VALUE
    elif (
        triggers
        and lock_key
        and str(all_data.get(lock_key)) == str(config.VERSION_LOCK_VALUE)
    ):
        triggers.clear()
        updates[Constants.VERSION_LOCK_FIELD] = config.VERSION_UNLOCK_VALUE
    return updates


def get_final_version_string(release_mode, version):
    """Generates update dictionary entries for the version string"""
    production_version = semver.finalize_version(version)
    updates = {}
    if release_mode:
        updates[Constants.RELEASE_FIELD] = config.RELEASED_VALUE
        updates[Constants.VERSION_FIELD] = production_version
        updates[Constants.VERSION_STRICT_FIELD] = production_version
    else:
        updates[Constants.VERSION_FIELD] = version
        updates[Constants.VERSION_STRICT_FIELD] = production_version
    return updates


def get_dvcs_info():
    """Gets current repository info from git"""
    cmd = "git rev-list --count HEAD"
    commit_count = str(
        int(subprocess.check_output(shlex.split(cmd)).decode("utf8").strip())
    )
    cmd = "git rev-parse HEAD"
    commit = str(subprocess.check_output(shlex.split(cmd)).decode("utf8").strip())
    return {Constants.COMMIT_FIELD: commit, Constants.COMMIT_COUNT_FIELD: commit_count}


def get_all_versions_from_tags(tags):
    # build a regex from our version template
    re_safe_placeholder = 10 * "v"
    tag_re = (
        "^"
        + re.escape(
            config.TAG_TEMPLATE.replace("{version}", re_safe_placeholder)
        ).replace(re_safe_placeholder, "(.*)")
        + "$"
    )
    _LOG.debug("regexing with %r", tag_re)
    tag_re_comp = re.compile(tag_re)
    matches = []
    for t in tags:
        match = tag_re_comp.match(t)
        if not match:
            continue
        matches.append(match.groups()[0])
    _LOG.debug("all versions matching regex %s", matches)
    return matches


def get_dvcs_commit_for_version(version, persist_from):
    """Given a previously tagged release version (and the tag template)

    Find the commit of that version
    """
    if persist_from == [Constants.FROM_SOURCE]:
        return None
    try:
        result = (
            subprocess.check_output(
                [
                    "git",
                    "rev-parse",
                    "--verify",
                    config.TAG_TEMPLATE.format(version=version),
                ]
            )
            .decode("utf8")
            .strip()
        )
        _LOG.debug("the commit of the last release is %s", result)
        return result
    except subprocess.CalledProcessError:
        _LOG.exception("failed to discover the commit for the last tagged release")


def get_dvcs_latest_tag_semver():
    """Gets the semantically latest tag across the whole repo"""
    tag_glob = config.TAG_TEMPLATE.replace("{version}", "*")
    cmd = "git tag --list %s" % tag_glob
    tags = str(subprocess.check_output(shlex.split(cmd)).decode("utf8").strip())
    tags = tags.splitlines()
    _LOG.debug("all tags matching simple pattern %r : %s", tag_glob, tags)
    matches = get_all_versions_from_tags(tags)
    ordered_versions = sorted(
        {v for v in set(utils.from_text_or_none(version) for version in matches) if v}
    )
    result = None
    if ordered_versions:
        result = ordered_versions.pop()
    _LOG.info("latest version found in across all dvcs tags: %s", result)
    return result


def get_dvcs_ancestor_tag_semver():
    """Gets the latest tag that's an ancestor to the current commit"""
    cmd = "git describe --abbrev=0 --tags"
    version = str(subprocess.check_output(shlex.split(cmd)).decode("utf8").strip())
    result = utils.from_text_or_none(get_all_versions_from_tags([version])[0])
    _LOG.info("latest version found in dvcs nearest tag: %r", result)
    return result


def add_dvcs_tag(version):
    """Sets a tag on the current commit"""
    cmd = 'git tag -a %s -m "version %s"' % (
        config.TAG_TEMPLATE.format(version=version),
        version,
    )
    version = str(subprocess.check_output(shlex.split(cmd)).decode("utf8").strip())
    return version


def get_current_version(persist_from):
    """Try loading the version from the sources in the order provided to us"""
    version = None
    for source in persist_from:
        if source == Constants.FROM_SOURCE:
            all_data = read_targets(config.targets)
            version = utils.get_semver_from_source(all_data)
        elif source == Constants.FROM_VCS_LATEST:
            version = get_dvcs_latest_tag_semver()
        elif source == Constants.FROM_VCS_ANCESTOR:
            version = get_dvcs_ancestor_tag_semver()
        if version:
            break
    return version


def get_overrides(updates, commit_count_as):
    overrides = {}
    if commit_count_as:
        _ = definitions.SemVerSigFig._asdict()[commit_count_as]
        commit_number = updates[Constants.COMMIT_COUNT_FIELD]
        _LOG.debug("using commit count for %s: %s", commit_count_as, commit_number)
        overrides[commit_count_as] = commit_number
    return overrides


def main(
    set_to=None,
    commit_count_as=None,
    release=None,
    bump=None,
    lock=None,
    enable_file_triggers=None,
    config_path=None,
    persist_from=None,
    persist_to=None,
    dry_run=None,
    **extra_updates
):
    """Main workflow.

    Load config from cli and file
    Detect "bump triggers" - things that cause a version increment
    Find the current version
    Create a new version
    Write out new version and any other requested variables

    :param set_to: explicitly set semver to this version string
    :param set_patch_count: sets the patch number to the commit count
    :param release: marks with a production flag
                just sets a single flag as per config
    :param bump: string indicating major/minor/patch
                more significant bumps will zero the less significant ones
    :param lock: locks the version string for the next call to autoversion
                lock only removed if a version bump would have occurred
    :param enable_file_triggers: whether to enable bumping based on file triggers
                bumping occurs once if any file(s) exist that match the config
    :param config_path: path to config file
    :param extra_updates:
    :return:
    """
    updates = {}
    persist_to = persist_to or [Constants.TO_SOURCE]
    persist_from = persist_from or [Constants.FROM_SOURCE]
    get_or_create_config(config_path, config)

    for k, v in config.regexers.items():
        config.regexers[k] = re.compile(v)

    # a forward-mapping of the configured aliases
    # giving <our config param> : <the configured value>
    # if a value occurs multiple times, we take the last set value
    # TODO: the 'forward aliases' things is way overcomplicated
    # would be better to rework the config to have keys set-or-None
    # since there's only a finite set of valid keys we operate on
    config._forward_aliases.clear()
    for k, v in config.key_aliases.items():
        config._forward_aliases[v] = k

    all_data = {}
    current_semver = get_current_version(persist_from)
    release_commit = get_dvcs_commit_for_version(current_semver, persist_from)
    new_semver = current_semver = str(current_semver)
    triggers = get_all_triggers(bump, enable_file_triggers, release_commit)
    updates.update(get_lock_behaviour(triggers, all_data, lock))
    updates.update(get_dvcs_info())

    if set_to:
        _LOG.debug("setting version directly: %s", set_to)
        # parse it - validation failure will raise a ValueError
        semver.parse(set_to)
        new_semver = set_to
        if not lock:
            warnings.warn(
                "After setting version manually, does it need locking for a CI flow, to avoid an extraneous increment?",
                UserWarning,
            )
    elif triggers:
        # only use triggers if the version is not set directly
        _LOG.debug("auto-incrementing version (triggers: %s)", triggers)
        overrides = get_overrides(updates, commit_count_as)
        new_semver = utils.make_new_semver(current_semver, triggers, **overrides)

    updates.update(get_final_version_string(release_mode=release, version=new_semver))

    # write out the individual parts of the version
    updates.update(semver.parse(new_semver))

    # only rewrite a field that the user has specified in the configuration
    native_updates = {
        native: updates[key]
        for native, key in config.key_aliases.items()
        if key in updates
    }

    # finally, add in commandline overrides
    native_updates.update(extra_updates)

    if not dry_run:
        if Constants.TO_SOURCE in persist_to:
            write_targets(config.targets, **native_updates)

        if Constants.TO_VCS in persist_to:
            add_dvcs_tag(updates[Constants.VERSION_FIELD])
    else:
        _LOG.warning("dry run: no changes were made")

    return current_semver, new_semver, native_updates


def parse_other_args(others):
    # pull extra kwargs from commandline, e.g. TESTRUNNER_VERSION
    updates = {}
    for kwargs in others:
        try:
            k, v = kwargs.split("=")
            _LOG.debug("parsing extra replacement from command line: %r = %r", k, v)
            updates[k.strip()] = ast.literal_eval(v.strip())
        except Exception:
            _LOG.exception(
                "Failed to unpack additional parameter pair: %r (ignored)", kwargs
            )
    return updates


def main_from_cli():
    """Main workflow.

    Load config from cli and file
    Detect "bump triggers" - things that cause a version increment
    Find the current version
    Create a new version
    Write out new version and any other requested variables
    """
    args, others = get_cli()

    if args.version:
        print(__version__)
        exit(0)

    log_level = logging.WARNING - 10 * args.verbosity
    logging.basicConfig(level=log_level, format="%(module)s %(levelname)8s %(message)s")

    command_line_updates = parse_other_args(others)

    old, new, updates = main(
        set_to=args.set,
        commit_count_as=args.commit_count_as,
        lock=args.lock,
        release=args.release,
        bump=args.bump,
        enable_file_triggers=args.file_triggers,
        config_path=args.config,
        dry_run=args.show,
        persist_from=args.persist_from,
        persist_to=args.persist_to,
        **command_line_updates
    )
    _LOG.info("previously: %s", old)
    _LOG.info("currently:  %s", new)
    _LOG.debug("updates:\n%s", pprint.pformat(updates))

    if args.print_file_triggers:
        commit = get_dvcs_commit_for_version(
            persist_from=args.persist_from, version=old
        )
        _, files = detect_file_triggers(commit)
        print("\n".join(files))
    else:
        print(new)


__name__ == "__main__" and main_from_cli()
