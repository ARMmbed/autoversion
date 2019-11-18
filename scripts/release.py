import os

import datetime
import logging
import subprocess
import sys
from git import Repo, Actor

ENVVAR_TWINE_USERNAME = 'TWINE_USERNAME'

NUMBER_OF_RETRIES = 5

ENVVAR_TWINE_REPOSITORY = 'TWINE_REPOSITORY'

ENVVAR_TWINE_REPOSITORY_URL = 'TWINE_REPOSITORY_URL'
ENVVAR_BRANCH_NAME = "CIRCLE_BRANCH"
ENVVAR_GITHUB_TOKEN = "GH_TOKEN"
ENVVAR_GITHUB_TOKEN2 = "GITHUB_TOKEN"
REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))


def change_remote(repo, github_token, branch_name):
    origin_url = repo.remotes.origin.url
    path = origin_url.split('github.com', 1)[1][1:].strip()
    new = 'https://{GITHUB_TOKEN}:x-oauth-basic@github.com/%s' % path
    logging.info('Rewriting git remote url to: %s' % new)
    repo.delete_remote(repo.remotes.origin)
    new_origin = repo.create_remote('origin',
                                    url=new.format(GITHUB_TOKEN=github_token)
                                    )
    repo.git.fetch()
    repo.git.checkout(branch_name)
    repo.git.branch(
        '--set-upstream-to', '%s/%s' % (new_origin, branch_name)
    )


def commit_release(repo, branch_name, version):
    logging.info("Committing release...")
    modified_files = [f.a_path for f in
                      repo.index.diff(None)] + repo.untracked_files
    if len(modified_files) == 0:
        logging.info(
            "No commit to perform as no changes were detected"
        )
        return
    repo.git.add('./src/auto_version/__version__.py')
    repo.git.add('CHANGELOG.md')
    repo.git.add('./docs/news/*')
    repo.git.tag()

    # Create commit
    author = Actor("monty bot", "monty-bot@arm.com")
    repo.config_writer().set_value("user", "name", author.name).release()
    repo.config_writer().set_value("user", "email", author.email).release()
    repo.index.commit(
        ":checkered_flag: :newspaper: Releasing version %s @ %s\n[ci skip]" % (
            version,
            datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        ),
        author=author
    )
    repo.create_tag(version, ref=branch_name, message='Release %s' % version)
    retries = NUMBER_OF_RETRIES
    while retries > 0:
        get_latest(repo, branch_name)
        if push_to_github(branch_name, repo):
            return
        retries = retries - 1
    raise Exception("Failed committing new release")
    mark_release_as_latest(branch_name, repo)


def mark_release_as_latest(branch_name, repo):
    logging.info('Marking this commit as latest')
    repo.create_tag('latest', force=True)
    while retries > 0:
        get_latest(repo, branch_name)
        if push_to_github(branch_name, repo, force=True):
            return
        retries = retries - 1
    raise Exception("Failed committing new release")


def push_to_github(branch_name, repo, force=False):
    logging.info("Pushing back to GitHub...")
    try:
        if force:
            repo.git.push('-f', '--set-upstream', repo.remotes.origin,
                          branch_name)
        else:
            repo.git.push('--follow-tags', '--set-upstream',
                          repo.remotes.origin,
                          branch_name)
        return True
    except Exception as e:
        logging.error("Push failed: %s" % str(e))
        return False


def get_latest(repo, branch_name):
    logging.info("Getting latest changes...")
    repo.git.checkout(branch_name)
    repo.git.fetch()
    repo.git.pull(repo.remotes.origin, branch_name)


def get_new_version():
    version = subprocess.check_output(
        ['python', 'setup.py', '--version']).decode().strip()
    if 'dev' in version:
        raise Exception('cannot release unversioned project: %s' % version)
    return version


def release_to_pypi(twine_repo, twine_username):
    logging.info('Releasing to %s as %s' % (twine_repo, twine_username))
    logging.info('Generating a release package')
    subprocess.check_call(
        ['python', 'setup.py', 'clean', '--all',
         'bdist_wheel',
         '--dist-dir', 'release-dist'])
    logging.info('Uploading to PyPI')
    subprocess.check_call(
        ['python', '-m', 'twine', 'upload', 'release-dist/*'])


def get_current_branch(repo):
    """Workaround  for this GitPython issue https://github.com/gitpython-developers/GitPython/issues/510"""
    try:
        return repo.active_branch
    except TypeError as e:
        logging.warning(
            "Could not determine the branch name using GitPython: %s" % str(e)
        )
        return os.getenv(ENVVAR_BRANCH_NAME)


def main():
    gh_token = os.getenv(ENVVAR_GITHUB_TOKEN) or os.getenv(
        ENVVAR_GITHUB_TOKEN2)
    # see:
    # https://packaging.python.org/tutorials/distributing-packages/#uploading-your-project-to-pypi
    twine_repo = os.getenv('%s' % ENVVAR_TWINE_REPOSITORY_URL) or os.getenv(
        ENVVAR_TWINE_REPOSITORY)
    twine_username = os.getenv(ENVVAR_TWINE_USERNAME)

    if not gh_token:
        logging.fatal(
            "Neither environment variables [%s] or [%s] (github token) are set. Aborting." % (
                ENVVAR_GITHUB_TOKEN, ENVVAR_GITHUB_TOKEN2)
        )
        sys.exit(1)
    if not twine_repo:
        logging.fatal(
            "Environment variables [%s/%s] (PyPI repository/URL) and/or [%s] (PyPI username) are not set. Aborting." % (
                ENVVAR_TWINE_REPOSITORY,
                ENVVAR_TWINE_REPOSITORY_URL,
                ENVVAR_TWINE_USERNAME)
        )
        sys.exit(1)
    this_repo = Repo(REPO_ROOT)
    logging.info("Releasing...")
    new_version = get_new_version()
    branch_name = get_current_branch(this_repo)
    logging.info("Current branch: %s" % str(branch_name))
    change_remote(this_repo, gh_token, branch_name)
    get_latest(this_repo, branch_name)
    commit_release(this_repo, branch_name, new_version)
    release_to_pypi(twine_repo, twine_username)
    logging.info('Done.')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
