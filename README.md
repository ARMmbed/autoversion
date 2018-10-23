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
usage: auto_version [-h] [--target TARGET] [--bump {major,minor,patch}]
                    [--news] [--set SET] [--set-patch-count] [--lock]
                    [--release] [--version] [--config CONFIG] [-v]

auto version: a tool to control version numbers

optional arguments:
  -h, --help            show this help message and exit
  --target TARGET       Files containing version info. Assumes unique variable
                        names between files. (default: ['src\\_version.py']).
  --bump {major,minor,patch}
                        Bumps the specified part of SemVer string. Use this
                        locally to correctly modify the version file.
  --news, --file-triggers
                        Detects need to bump based on presence of files (as
                        specified in config).
  --set SET             Set the SemVer string. Use this locally to set the
                        project version explicitly.
  --set-patch-count     Sets the patch number to the commit count.
  --lock                Locks the SemVer string. Lock will remain for another
                        call to autoversion before being cleared.
  --release             Marks as a release build, which flags the build as
                        released.
  --version             Prints the version of auto_version itself (self-
                        version).
  --config CONFIG       Configuration file path.
  -v, --verbosity       increase output verbosity. can be specified multiple
                        times
```
