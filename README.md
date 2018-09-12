# auto_version
Cross-language tool written in Python to automatically version projects using [SemVer](https://semver.org/)

[![CircleCI](https://circleci.com/gh/ARMmbed/autoversion.svg?style=svg)](https://circleci.com/gh/ARMmbed/autoversion)

```
pipenv install https://github.com/ARMmbed/autoversion
```

## usage
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
## notes
### fundamentals
The tool operates on any text files, but _find and replacing_ variables
configured in the tool. This makes it cross-language compatible and easily
extensible.
- `target` adds a file to the list of files containing variables to replace
- `?=?` any extra commands to the tool are treated as additional `key=value` pairs
to replace
### manual
The tool can be used manually, locally, to manage version changes, e.g.
- `set` to set the exact version
- `bump` to increment part of the SemVer
### stateless
In this mode, the version number is determined from the version control commit distance.
Only `git` dvcs is supported.
- `set-patch-count` will use the commit count for the patch number
- the patch number can also be used in the _devmode template_ e.g. `4.5.6dev789`
  - major: 4
  - minor: 5
  - patch: 6
  - 'dev' release
  - sub-patch: 789
### stateful
In this mode, version state information is committed back into the repository.
Typically this would occur on a successful release.
- `release` is used for strictly production version strings (i.e. _not_ devmode)
- `file-triggers` (aka `news`) will trigger a certain version bump based on the presence
of other files. This is intended for use with newsfile release flows
(e.g. [towncrier](https://pypi.org/project/towncrier/)).
### advanced
Combining manual and automated versioning:
- `lock`: when releasing through a CI flow, a naive stateful system would always increment,
even when the developer wishes to `bump` or `set` the version locally.
If a `lock` variable can be set (somewhere in the repo), the current version is maintained
for exactly one iteration of a CI release. Whereever `auto_version` would have changed the
version number, it instead removes the lock, such that increments resume on the next iteration.
- (config file) `VERSION_KEY_STRICT`: provides a version string that is always equivalent to
a `release` version
- (config file) `regexers`: configure custom regexes for different file types
(for detection and substitution of key-value pairs)
- (config file) `trigger_patterns`: describes file triggers for use with `news`
- (config file) `DEVMODE_TEMPLATE`: sets a template for _devmode_ releases

### configuration
- `config` path to a configuration file in [toml format](https://github.com/toml-lang/toml).
If the file does not exist, it will be created with defaults.

## getting started
1. install `auto_version`
1. run `auto_version --config=desired/config/path`
1. adjust the configuration as necessary. in particular, set `targets` to a list of
files in your project that contain variables for the tool to update.
   1. fields under `key_aliases` map from your project to `auto_version`;
values on the left are the variable names exactly as they appear in your project files.
1. run `auto_version --config=desired/config/path` to have the tool print out
the currently detected version. You may need to readjust the config.
1. run `auto_version --config=desired/config/path --bump=patch -vv` to try an initial
version increment, and view details on the updates the tool has applied.
Check your target files, and if they are as you'd expect then you're good to go.
