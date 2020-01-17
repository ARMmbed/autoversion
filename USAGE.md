# Autoversion Usage Guide
The tool operates on any text files, by running a regex find-and-replace on
variables configured by your project. This makes it cross-language compatible and easily
extensible.

New version numbers are set by finding the existing version number, determining
the new version number, and writing it back to the file.

## Suggested workflows
- Incrementing version numbers in source code, and pushing back to a repository
- Incrementing version numbers in source code before a build
- Automatically storing version numbers in git tags
  - tags are globally unique so provide an assurance that versions are also unique
- Controlling version increments using newsfiles
- ... or all of the above!

## Setting target files
- `target` adds a file to the list of files containing variables to replace
- all matching variables are replaced in all target files
- any variables that aren't found trigger a failure

## Sourcing a version number
`persist-from` defines where to load the version number from.
This can be used multiple times and operates in order. Once a version
is found, it stops looking.

- `source` - expects to find the version number by looking in the `targets`
- `vcs...` - git repo support. Looks for git tags matching the `TAG_TEMPLATE`. Various options
allow control of which version to start from. Versions can be anything
(including pre-releases) or only strictly released versions. They can be
found globally across the repo, or only on commits prior to the current commit.
  - `vcs-prev-version` - previous version on this branch ancestry
  - `vcs-prev-release` - previous release on this branch ancestry
  - `vcs-global-version` - globally latest previous version on _any_ branch
  - `vcs-global-release` - globally latest previous release on _any_ branch

`persist-to` defines where to write the modified version numbers to.
- `source` - the default, writes back to the source code. `autoversion` does **not** make any commits.
- `vcs` - tags the current repository commit with the new version, according to the `TAG_TEMPLATE`.
  `autoversion` does **not** push any tags.

## Replacements
- Passing extra arguments on the CLI `?=?` lets you set arbitrary `key=value` replacement pairs.
  This might be used in a CI system to pass in a build number.
- More commonly you will use `key_aliases` defined in the config to set
values from `autoversion`'s internal parameters:

| Alias                | Example value set by `autoversion` | Notes                                                                          |
|----------------------|------------------------------------|--------------------------------------------------------------------------------|
| "VERSION_KEY"        | 1.2.3-pre.1                        | The new version number                                                         |
| "VERSION_KEY_STRICT" | 1.2.3                              | The new version number but _only_ ever a release version (three sig-figs)      |
| "RELEASE_FIELD"      | True or False                      | A boolean indicating this was a release                                        |
| "VERSION_LOCK"       | True or False                      | A boolean indicating this version is locked for the next call of `autoversion` |
| "COMMIT_COUNT"       | 1324                               | The count of all commits from the start of history to this commit              |
| "COMMIT"             | abc123def456                       | The sha of the current commit                                                  |
| "major"              | 1                                  | One part of the semver version                                                 |
| "minor"              | 2                                  | One part of the semver version                                                 |
| "patch"              | 3                                  | One part of the semver version                                                 |

## Manual
The tool can be used manually, locally, to manage version changes, e.g.
- `set 4.5.6` to set the exact version to _4.5.6_
- `bump minor` to increment part of the SemVer e.g. _4.5.6_ to _4.6.0_

## File Triggers (aka News)
This functionality supports the use of newsfile-based versioning.

Newsfiles are small snippets of text that are used to build changelogs. By
categorising the newsfiles in to the significance of their changes,
`autoversion` can determine what the next version number should be.

See [towncrier](https://pypi.org/project/towncrier/) for more information
on newsfiles (and to automate your changelog generation too!)

Pass `file-triggers` or `news` on the CLI. This will trigger a certain version bump based on the presence
of other files. Configure the file triggers with the `trigger_patterns` config
dictionary. e.g.

1. `12.feature` file has been added
1. `feature` was mapped to `minor`
1. `minor` version increment is made

This can be combined with the VCS sourcing to only consider files
added since the previous version.

### `incr-from-release`
This CLI flag enables more accurate automated versioning, and requires both `news` and `persist-from=vcs-*`

This is intended to more fully implement the logic behind semantic versioning
_given_ our knowledge about the semantics of the changes that have been made.
It ensures the new version correctly represents the most significant change
made since the previous release.

1. starting at the latest release **1.2.3**
1. a new _bugfix_ is added
1. this would result in **1.2.4-pre.1**
1. another developer adds another _bugfix_
1. we are now at **1.2.4-pre.2** (i.e. prerelease continues incrementing)
1. but if another developer now adds a _feature_
1. we are now at **1.3.0-pre.1** (i.e. features are more significant
 than bugfixes, so we start the prerelease again)

## Commit Count
Commit count is the version control commit distance over all time.
It's not unique across branches, but can be used to good effect if versioning is
performed on a single trunk/master branch.

- `commit-count-as=minor|patch|prerelease|build` will use the commit count (e.g. 789) for the specified field

## Locking
- used if combining manual and automated version increments.
- when releasing through a CI flow, a naive stateful system would always increment,
even when the developer wishes to `bump` or `set` the version locally.
If a `lock` variable can be set (somewhere in the repo), the current version is maintained
for exactly one iteration of a CI release. On the next run, if `auto_version` would have changed the
version number, it instead removes the lock, such that increments resume on the next iteration.
- pass `lock` on the CLI to set the lock flag
