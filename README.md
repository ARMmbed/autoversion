# Autoversion
[Semantically version](https://semver.org/) any project in any language!

[Contributions](./CONTRIBUTING.md) welcome.

[![CircleCI](https://circleci.com/gh/ARMmbed/autoversion.svg?style=svg&circle-token=dd9ec017be37f9b5f0a5b9a785c55c53fcd578c7)](https://circleci.com/gh/ARMmbed/autoversion)

[![PyPI version](https://badge.fury.io/py/pyautoversion.svg)](https://badge.fury.io/py/pyautoversion)

## [Documentation](./USAGE.md)

## Quickstart
1. You'll need Python 2 or 3

1. Install
    ```
    pip install pyautoversion
    ```
1. Run `auto_version`
    - the default config file is `pyproject.toml` at the root of your project.
    - use `--config=path/to/config.toml` to customise the config path.
     It must be in [toml format](https://github.com/toml-lang/toml).
      If the file does not exist, it will be created with some example values.
1. Adjust the configuration as necessary. In particular, set `targets` to a list of
files in your project that contain variables for the tool to update.
    ```
    [tool.autoversion]
    targets = [
    "path/to/version/file"
    ]
    [tool.autoversion.key_aliases]
    __version__ = "VERSION_KEY"
    ```
    - `key_aliases` maps source code keys from your project into `auto_version`
    [data fields](./USAGE.md).
values on the left are the variable names exactly as they appear in your project files;
for example in _python_ you might have this line of code in a file:
    ```
    __version__ = "1.2.3"
    ```
1. Run `auto_version` again to have the tool print out
the currently detected version. If this doesn't work, you may need to readjust the config.
    ```
    >>> 1.2.3
    ```

1. Run `auto_version --bump=patch --release -vv` to try an initial
version increment, and view verbose details on the updates the tool has applied.
Check your target files, and if they are as you'd expect then you're good to go!
    ```
    >>> 1.2.4
    ```
    and the contents of the file would be:
    ```
    __version__ = "1.2.4"
    ```

## CLI
These options are explained further in the [documentation](./USAGE.md)

```
>>> autoversion --help
usage: auto_version [-h] [--show] [--bump {major,minor,patch,prerelease,build}] [--news] [--incr-from-release] [--print-file-triggers] [--set SET]
                    [--commit-count-as {major,minor,patch,prerelease,build}] [--lock] [--release] [--version]
                    [--persist-from {vcs-global-version,vcs-global-release,vcs-prev-version,source,vcs-prev-release}] [--persist-to {vcs,source}] [--config CONFIG]
                    [-v]

auto version v1.1.0: a tool to control version numbers

optional arguments:
  -h, --help            show this help message and exit
  --show, --dry-run     Don't write anything to disk or vcs.
  --bump {major,minor,patch,prerelease,build}
                        Bumps the specified part of SemVer string. Use this locally to correctly modify the version file.
  --news, --file-triggers
                        Detects need to bump based on presence of files (as specified in config).
  --incr-from-release   Automatically sets version number based on SCIENCE (see docs). Requires use of VCS tags.
  --print-file-triggers
                        Prints a newline separated list of files detected as bump triggers.
  --set SET             Set the SemVer string. Use this locally to set the project version explicitly.
  --commit-count-as {major,minor,patch,prerelease,build}
                        Use the commit count to set the value of the specified field.
  --lock                Locks the SemVer string. Lock will remain for another call to autoversion before being cleared.
  --release             Marks as a release build, which flags the build as released.
  --version             Prints the version of auto_version itself (self-version).
  --persist-from {vcs-global-version,vcs-global-release,vcs-prev-version,source,vcs-prev-release}
                        Where the current version is stored. Looks for each source in order. (default: source files)
  --persist-to {vcs,source}
                        Where the new version is stored. This could be in multiple places at once. (default: source files)
  --config CONFIG       Configuration file path. (default: /home/david/coding/autoversion/pyproject.toml).
  -v, --verbosity       increase output verbosity. can be specified multiple times
```

# Other tools
These tools are variously inspirations, alternatives, or complementary
to `autoversion`.

| Project                                                    | Observations                                                                                                              |
|------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| [towncrier](https://pypi.org/project/towncrier/)           | Automates changelog generation using newsfiles.                                                                           |
| [incremental](https://pypi.org/project/incremental/)       | A python-specific versioning tool. Has some support for [CalVer](https://calver.org/).                                    |
| [setuptools_scm](https://pypi.org/project/setuptools-scm/) | A python-specific versioning tool.                                                                                        |
| [bump2version](https://pypi.org/project/bump2version/)     | A source-code versioning tool. Doesn't support newsfile detection. Highly configurable substitutions on a per-file basis. |
| [semver](https://pypi.org/project/semver/)                 | _The_ python semantic version manipulation library.                                                                       |
| [semver spec](https://semver.org/)                         | More like guidelines than actual rules.                                                                                   |
