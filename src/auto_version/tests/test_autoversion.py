import contextlib
import functools
import imp
import os
import re
import shlex
import subprocess
import unittest

import semver
import six
from auto_version import auto_version_tool
from auto_version import utils
from auto_version.auto_version_tool import extract_keypairs
from auto_version.auto_version_tool import get_all_versions_from_tags
from auto_version.auto_version_tool import main
from auto_version.auto_version_tool import replace_lines
from auto_version.config import AutoVersionConfig as config
from auto_version.config import Constants
from auto_version.replacement_handler import ReplacementHandler


class TestBumps(unittest.TestCase):
    call = functools.partial(main, config_path="example.toml")

    @classmethod
    def setUpClass(cls):
        dir = os.path.dirname(__file__)
        os.chdir(os.path.abspath(dir))

    def tearDown(self):
        self.call(set_to="19.99.0")

    def test_bump_patch(self):
        old, new, updates = self.call(bump="patch", release=True)
        self.assertEqual(
            updates,
            {
                "RELEASE": True,
                "VERSION": "19.99.1",
                "VERSION_AGAIN": "19.99.1",
                "STRICT_VERSION": "19.99.1",
            },
        )

    def test_bump_major(self):
        old, new, updates = self.call(bump="major", release=True)
        self.assertEqual(
            updates,
            {
                "RELEASE": True,
                "VERSION": "20.0.0",
                "VERSION_AGAIN": "20.0.0",
                "STRICT_VERSION": "20.0.0",
            },
        )

    def test_bump_news(self):
        old, new, updates = self.call(enable_file_triggers=True, release=True)
        self.assertEqual(
            updates,
            {
                "RELEASE": True,
                "VERSION": "19.100.0",
                "VERSION_AGAIN": "19.100.0",
                "STRICT_VERSION": "19.100.0",
            },
        )

    def test_dev(self):
        old, new, updates = self.call(bump="prerelease")
        self.assertEqual(
            updates,
            {
                "VERSION": "19.99.1-dev.1",
                "VERSION_AGAIN": "19.99.1-dev.1",
                "STRICT_VERSION": "19.99.1",
            },
        )

    def test_build(self):
        # can't just tag a build onto something that's already a release version
        self.call(set_to="19.99.0+build.1")
        old, new, updates = self.call(bump="build")
        self.assertEqual(
            updates,
            {
                "VERSION": "19.99.0+build.2",
                "VERSION_AGAIN": "19.99.0+build.2",
                "STRICT_VERSION": "19.99.0",
            },
        )

    def test_non_release_bump(self):
        old, new, updates = self.call(bump="minor")
        self.assertEqual(
            updates,
            {
                "VERSION": "19.100.0-dev.1",
                "VERSION_AGAIN": "19.100.0-dev.1",
                "STRICT_VERSION": "19.100.0",
            },
        )

    def test_invalid_bump(self):
        with self.assertRaises(KeyError):
            self.call(bump="banana")

    def test_increment_existing_prerelease(self):
        old, new, updates = self.call(set_to="1.2.3-RC.1")
        self.assertEqual(new, "1.2.3-RC.1")
        old, new, updates = self.call(bump="prerelease")
        self.assertEqual(new, "1.2.3-RC.2")

    def test_end_to_end(self):
        self.call(bump="major")
        filepath = os.path.join(os.path.dirname(__file__), "example.py")
        example = imp.load_source("example", filepath)
        self.assertEqual(example.VERSION, "20.0.0-dev.1")

    def test_simple_config_bump(self):
        old, new, updates = self.call(config_path="simple.toml", bump="minor")
        self.assertEqual(new, "19.100.0-dev.1")
        # do our own teardown...
        self.call(config_path="simple.toml", set_to="19.99.0")

    def test_custom_field_set(self):
        old, new, updates = self.call(UNRELATED_STRING="apple")
        self.assertEqual(updates["UNRELATED_STRING"], "apple")


class TestUtils(unittest.TestCase):
    def test_is_release(self):
        self.assertTrue(utils.is_release(semver.parse_version_info("1.2.3")))
        self.assertFalse(utils.is_release(semver.parse_version_info("1.2.3-RC.1")))
        self.assertFalse(utils.is_release(semver.parse_version_info("1.2.3+abc")))

    def test_sigfig_max(self):
        self.assertEqual("minor", utils.max_sigfig(["minor", "patch"]))

    def test_sigfig_min(self):
        self.assertEqual("minor", utils.min_sigfig(["minor", "major"]))

    def test_sigfig_compare_gt(self):
        self.assertFalse(utils.sigfig_gt("minor", "major"))
        self.assertFalse(utils.sigfig_gt("minor", "minor"))
        self.assertTrue(utils.sigfig_gt("major", "patch"))

    def test_sigfig_compare_lt(self):
        self.assertTrue(utils.sigfig_lt("minor", "major"))
        self.assertFalse(utils.sigfig_lt("minor", "minor"))
        self.assertFalse(utils.sigfig_lt("major", "patch"))

    def test_semver_diff(self):
        self.assertEqual(
            "minor",
            utils.semver_diff(
                semver.parse_version_info("1.2.3"), semver.parse_version_info("1.3.5")
            ),
        )
        self.assertEqual(
            "patch",
            utils.semver_diff(
                semver.parse_version_info("1.2.3"),
                semver.parse_version_info("1.2.4-RC.1"),
            ),
        )
        self.assertEqual(
            None,
            utils.semver_diff(
                semver.parse_version_info("1.2.3"), semver.parse_version_info("1.2.3")
            ),
        )


class TestNewSemVerLogic(unittest.TestCase):
    """Unit testing the core logic that determines a bump"""

    @classmethod
    def setUpClass(cls):
        test_dir = os.path.dirname(__file__)
        auto_version_tool.load_config(os.path.join(test_dir, "example.toml"))

    def check(self, previous, current, bumps, expect):
        previous = semver.parse_version_info(previous) if previous else None
        self.assertEqual(
            expect,
            str(
                utils.make_new_semver(
                    semver.parse_version_info(current), previous, bumps
                )
            ),
        )

    def test_release_bump(self):
        self.check(None, "1.2.3", {"minor"}, "1.3.0-dev.1")

    def test_no_history_bump(self):
        self.check(None, "1.2.3", {"prerelease"}, "1.2.4-dev.1")

        # this would be wrong, because you can't pre-release something that's released
        # self.check(None, "1.2.3", ["prerelease"], "1.2.3-dev.1")

    def test_no_history_pre_bump(self):
        self.check(None, "1.2.3-dev.1", {"prerelease"}, "1.2.3-dev.2")

    def test_release_bump_with_history(self):
        self.check("1.2.2", "1.2.3", {"minor"}, "1.3.0-dev.1")

    def test_candidate_bump_with_history_less(self):
        # the bump is less significant than the original RC increment
        self.check("1.0.0", "1.1.0-dev.3", {"patch"}, "1.1.0-dev.4")

    def test_candidate_bump_with_history_same(self):
        # the RC has the same significance from the previous release as the bump
        self.check("1.2.2", "1.2.3-dev.1", {"patch"}, "1.2.3-dev.2")

    def test_candidate_bump_with_history_more(self):
        # the bump is more significant than the previous release, so perform that bump
        self.check("1.2.2", "1.2.3-dev.1", {"minor"}, "1.3.0-dev.1")


class TestVCSTags(unittest.TestCase):
    call = functools.partial(main, config_path="example.toml")

    @classmethod
    def setUpClass(cls):
        dir = os.path.dirname(__file__)
        os.chdir(os.path.abspath(dir))

    @classmethod
    def tearDownClass(cls):
        cls.call(set_to="19.99.0")

    def setUp(self):
        cmd = "git tag release/4.5.6"
        subprocess.check_call(shlex.split(cmd))
        cmd = "git tag release/4.5.7-dev.1"
        subprocess.check_call(shlex.split(cmd))
        # todo: build a git tree with a branch, release and RC on that branch
        # (to distinguish global vs ancestry tests)
        self.addCleanup(
            subprocess.check_call, shlex.split("git tag --delete release/4.5.7-dev.1")
        )
        self.addCleanup(
            subprocess.check_call, shlex.split("git tag --delete release/4.5.6")
        )

    def test_from_ancestor_version(self):
        bumped = "4.5.7-dev.1"
        old, new, updates = self.call(
            persist_from=[Constants.FROM_VCS_PREVIOUS_VERSION]
        )
        self.assertEqual(
            updates,
            {
                "VERSION": bumped,
                "VERSION_AGAIN": bumped,
                "STRICT_VERSION": semver.finalize_version(bumped),
            },
        )

    def test_from_ancestor_release(self):
        bumped = "4.5.6"
        old, new, updates = self.call(
            persist_from=[Constants.FROM_VCS_PREVIOUS_RELEASE]
        )
        self.assertEqual(
            updates,
            {
                "VERSION": bumped,
                "VERSION_AGAIN": bumped,
                "STRICT_VERSION": semver.finalize_version(bumped),
            },
        )

    def test_from_latest_of_all_time(self):
        bumped = "4.5.7-dev.1"
        old, new, updates = self.call(persist_from=[Constants.FROM_VCS_LATEST_VERSION])
        self.assertEqual(
            updates,
            {
                "VERSION": bumped,
                "VERSION_AGAIN": bumped,
                "STRICT_VERSION": semver.finalize_version(bumped),
            },
        )

    def test_from_latest_of_all_time_release(self):
        bumped = "4.5.6"
        old, new, updates = self.call(persist_from=[Constants.FROM_VCS_LATEST_RELEASE])
        self.assertEqual(
            updates,
            {
                "VERSION": bumped,
                "VERSION_AGAIN": bumped,
                "STRICT_VERSION": semver.finalize_version(bumped),
            },
        )

    def test_to_tag(self):
        """writes a tag in to git
        """
        bumped = "5.0.0-dev.1"
        old, new, updates = self.call(
            persist_from=[Constants.FROM_VCS_LATEST_VERSION],
            persist_to=[Constants.TO_VCS],
            bump="major",
        )
        self.addCleanup(
            subprocess.check_call, shlex.split("git tag --delete release/5.0.0-dev.1")
        )
        self.assertEqual(
            updates,
            {
                "VERSION": bumped,
                "VERSION_AGAIN": bumped,
                "STRICT_VERSION": semver.finalize_version(bumped),
            },
        )
        version = auto_version_tool.get_dvcs_repo_latest_version_semver()
        self.assertEqual(
            dict(version._asdict()),
            dict(major=5, minor=0, patch=0, build=None, prerelease="dev.1"),
        )


class TestTagReplacements(unittest.TestCase):
    some_tags = [
        "0.0.0",
        "0.1.0",
        "v0.2.0",
        "0.3.0v",
        "my_project/0.4.0",
        "my_project/0.5.0/releases",
        "my_project/0.6.0-RC.2+build-99/releases",
        r"£*ORWI\H'#[;'Q",
    ]

    @classmethod
    def setUpClass(cls):
        cls._default_template = config.TAG_TEMPLATE

    @classmethod
    def tearDownClass(cls):
        config.TAG_TEMPLATE = cls._default_template

    def eval(self, template, tags, expect):
        config.TAG_TEMPLATE = template
        self.assertEqual(get_all_versions_from_tags(tags), expect)

    def test_empty_tag(self):
        self.eval("", self.some_tags, [])

    def test_v_tag(self):
        self.eval("v{version}", self.some_tags, ["0.2.0"])

    def test_plain_tag(self):
        self.eval("{version}", self.some_tags, ["0.0.0", "0.1.0"])

    def test_prefix_tag(self):
        self.eval("my_project/{version}", self.some_tags, ["0.4.0"])

    def test_prefix_suffix_tag(self):
        self.eval(
            "my_project/{version}/releases",
            self.some_tags,
            ["0.5.0", "0.6.0-RC.2+build-99"],
        )


@contextlib.contextmanager
def Noop():
    """A no-op context manager"""
    yield


class BaseReplaceCheck(unittest.TestCase):
    key = "custom_Key"
    value = "1.2.3.4+dev0"
    value_replaced = "5.6.7.8+dev1"
    regexer = None
    lines = []  # simply specify the line if it's trivial to do ''.replace() with
    explicit_replacement = {}  # otherwise, specify the line, and the output
    non_matching = []  # specify example lines that should not match

    def test_match(self):
        """
        Check that for each specified line, a match is triggered

        n.b. a match must include the full length of the line, or nothing at all

        if it includes the full length of the line, there must be two named groups
        `KEY` and `VALUE` that contain only the key and value respectively

        :return:
        """
        for line in self.lines:
            with self.subTest(line=line) if six.PY3 else Noop():
                extracted = extract_keypairs([line], self.regexer)
                self.assertEqual({self.key: self.value}, extracted)

    def test_non_match(self):
        """
        Check lines that shouldn't trigger any matches
        :return:
        """
        for line in self.non_matching:
            with self.subTest(line=line) if six.PY3 else Noop():
                extracted = extract_keypairs([line], self.regexer)
                self.assertEqual({}, extracted)

    def test_replace(self):
        """
        takes all the 'lines' and generates an expected value with a simple replacement
        (1.2.3.4+dev0 -> 5.6.7.8+dev1)
        additionally, explicit replacements can be tested
        they are all run through the ReplacementHandler to check
        the expected value
        """

        replacements = {}
        replacements.update(self.explicit_replacement)
        replacements.update(
            {k: k.replace(self.value, self.value_replaced) for k in self.lines}
        )
        for line, replaced in replacements.items():
            with self.subTest(line=line) if six.PY3 else Noop():
                extracted = replace_lines(
                    self.regexer,
                    ReplacementHandler(**{self.key: self.value_replaced}),
                    [line],
                )
                self.assertEqual([replaced], extracted)


class PythonRegexTest(BaseReplaceCheck):
    regexer = re.compile(config.regexers[".py"], flags=re.DOTALL)
    lines = [
        'custom_Key = "1.2.3.4+dev0"\r\n',
        '    custom_Key = "1.2.3.4+dev0"\r\n',
        '    custom_Key: "1.2.3.4+dev0",\r\n',
    ]
    non_matching = ['# custom_Key = "1.2.3.4+dev0"\r\n']


class JSONRegexTest(BaseReplaceCheck):
    regexer = re.compile(config.regexers[".json"])
    lines = [
        '"custom_Key": "1.2.3.4+dev0"\r\n',
        '    "custom_Key" : "1.2.3.4+dev0",\r\n',
    ]


class JSONBoolRegexTest(BaseReplaceCheck):
    regexer = re.compile(config.regexers[".json"])
    value = "false"
    value_replaced = "true"
    key = "is_production"
    lines = []
    explicit_replacement = {'"is_production": false,\r\n': '"is_production": true,\r\n'}


class PropertiesRegexTest(BaseReplaceCheck):
    regexer = re.compile(config.regexers[".properties"])
    lines = ["custom_Key=1.2.3.4+dev0\r\n", "    custom_Key = 1.2.3.4+dev0\r\n"]
    explicit_replacement = {"custom_Key=\r\n": "custom_Key=5.6.7.8+dev1\r\n"}


class CSharpRegexTest(BaseReplaceCheck):
    regexer = re.compile(config.regexers[".cs"])
    lines = ['  public const string custom_Key = "1.2.3.4+dev0";  // auto\r\n']
    non_matching = [
        '// <copyright file="Version.cs" company="Arm">\r\n',
        '//  public const string custom_Key = "1.2.3.4+dev0";  // auto\r\n',
    ]
    explicit_replacement = {
        # check for no-op on these comment strings that contain variable assignment
        '// <copyright file="Version.cs" company="Arm">': '// <copyright file="Version.cs" company="Arm">',
        '// <copyright file="Version.cs" company="Arm">\r\n': '// <copyright file="Version.cs" company="Arm">\r\n',
    }


class XMLRegexTest(BaseReplaceCheck):
    regexer = re.compile(config.regexers[".csproj"])
    lines = ["  <custom_Key>1.2.3.4+dev0</custom_Key>\r\n"]
    non_matching = [
        '<Project Sdk="Microsoft.NET.Sdk">\r\n',
        """<PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Release|AnyCPU'">\r\n""",
    ]


class YamlRegexTest(BaseReplaceCheck):
    regexer = re.compile(config.regexers[".yaml"])
    lines = [
        """  "custom_Key": '1.2.3.4+dev0'\r\n""",
        """  custom_Key: 1.2.3.4+dev0""",
        """  custom_Key: 1.2.3.4+dev0  # comment""",
    ]
    explicit_replacement = {
        "    name: python:3.7.1\r\n": "    name: python:3.7.1\r\n",
        " custom_Key: 1.2.3.4+dev0  # yay": " custom_Key: 5.6.7.8+dev1  # yay",
        "    CTEST_ARGS: -L node_cpu\r\n": "    CTEST_ARGS: -L node_cpu\r\n",
    }
    non_matching = ["""entrypoint: [""]\r\n"""]  # don't match on empty arrays
