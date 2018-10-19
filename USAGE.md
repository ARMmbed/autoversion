# Autoversion
The tool operates on any text files, by _finding and replacing_ variables
configured in the tool. This makes it cross-language compatible and easily
extensible. New version numbers are set by finding the existing version in one of the target files, determining
the new version number, and writing it back to the file.
- `target` adds a file to the list of files containing variables to replace
- `?=?` any extra commands to the tool are treated as additional `key=value` pairs
to replace

### Manual
The tool can be used manually, locally, to manage version changes, e.g.
- `set 4.5.6` to set the exact version to _4.5.6_
- `bump minor` to increment part of the SemVer e.g. _4.5.6_ to _4.6.0_

### Stateless
In this mode, the version number is determined from the version control commit distance.
Only `git` dvcs is supported.
- `set-patch-count` will use the commit count (e.g. 789) for the patch number
  - commit count is taken to be the count of ancestors of the head of the current branch
- the patch number can also be substituted in the _devmode template_ e.g. `4.5.6dev789`
  - major: 4
  - minor: 5
  - patch: 6
  - 'dev' release
  - sub-patch: 789

### Stateful
In this mode, version state information is expected to be committed back into the repository.
Typically this would occur on a successful release. `auto_version` does not manipulate
the repository index - this is left to the project's CI tooling.
- `release` is used for strictly production version strings (i.e. _not_ devmode)
- `file-triggers` (aka `news`) will trigger a certain version bump based on the presence
of other files. This is intended for use with newsfile release flows
(e.g. [towncrier](https://pypi.org/project/towncrier/)).

### Advanced
Combining manual and automated versioning:
- `lock`: when releasing through a CI flow, a naive stateful system would always increment,
even when the developer wishes to `bump` or `set` the version locally.
If a `lock` variable can be set (somewhere in the repo), the current version is maintained
for exactly one iteration of a CI release. On the next run, if `auto_version` would have changed the
version number, it instead removes the lock, such that increments resume on the next iteration.
- (config file) `VERSION_KEY_STRICT`: provides a version string that is always equivalent to
a `release` version
- (config file) `regexers`: configure custom regexes for different file types
(for detection and substitution of key-value pairs)
- (config file) `trigger_patterns`: describes file triggers for use with `news`
- (config file) `DEVMODE_TEMPLATE`: sets a template for _devmode_ releases
