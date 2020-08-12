# Autoversion
Cross-language tool written in Python to automatically version projects using [SemVer](https://semver.org/)

[![CircleCI](https://circleci.com/gh/ARMmbed/autoversion.svg?style=svg&circle-token=dd9ec017be37f9b5f0a5b9a785c55c53fcd578c7)](https://circleci.com/gh/ARMmbed/autoversion)

[![PyPI version](https://badge.fury.io/py/pyautoversion.svg)](https://badge.fury.io/py/pyautoversion)



## Getting started
1. install `auto_version`
```
pipenv install pyautoversion
```
2. run `auto_version --config=desired/config/path`
    - `desired/config/path`: path to a configuration file in [toml format](https://github.com/toml-lang/toml).
      If the file does not exist, it will be created with defaults.
3. adjust the configuration as necessary. in particular, set `targets` to a list of
files in your project that contain variables for the tool to update.
    - fields under `key_aliases` map from your project to `auto_version`;
values on the left are the variable names exactly as they appear in your project files.
4. run `auto_version --config=desired/config/path` to have the tool print out
the currently detected version. You may need to readjust the config.
5. run `auto_version --config=desired/config/path --bump=patch -vv` to try an initial
version increment, and view details on the updates the tool has applied.
Check your target files, and if they are as you'd expect then you're good to go.


## Usage
For more details about how to use the tool, have a look at the [usage page](./USAGE.md)

```
usage: auto_version [-h] [--show]
                    [--bump {major,minor,patch,prerelease,build}] [--news]
                    [--print-file-triggers] [--set SET]
                    [--commit-count-as {major,minor,patch,prerelease,build}]
                    [--lock] [--release] [--version]
                    [--persist-from {vcs,vcs-latest,source}]
                    [--persist-to {vcs,source}] [--config CONFIG] [-v]

auto version v1.2.0: a tool to control version numbers

optional arguments:
  -h, --help            show this help message and exit
  --show, --dry-run     Don't write anything to disk or vcs.
  --bump {major,minor,patch,prerelease,build}
                        Bumps the specified part of SemVer string. Use this
                        locally to correctly modify the version file.
  --news, --file-triggers
                        Detects need to bump based on presence of files (as
                        specified in config).
  --print-file-triggers
                        Prints a newline separated list of files detected as
                        bump triggers.
  --set SET             Set the SemVer string. Use this locally to set the
                        project version explicitly.
  --commit-count-as {major,minor,patch,prerelease,build}
                        Use the commit count to set the value of the specified
                        field.
  --lock                Locks the SemVer string. Lock will remain for another
                        call to autoversion before being cleared.
  --release             Marks as a release build, which flags the build as
                        released.
  --version             Prints the version of auto_version itself (self-
                        version).
  --persist-from {vcs,vcs-latest,source}
                        Where the current version is stored. Looks for each
                        source in order. (default: source files)
  --persist-to {vcs,source}
                        Where the new version is stored. This could be in
                        multiple places at once. (default: source files)
  --config CONFIG       Configuration file path. (default:
                        C:\Users\adrcab01\OneDrive -
                        Arm\Documents\GitHub\mbed-targets\pyproject.toml).
  -v, --verbosity       increase output verbosity. can be specified multiple
                        times
```
