import contextlib
import functools
import imp
import os
import re
import shlex
import subprocess
import unittest

import six
from auto_version import auto_version_tool
from auto_version.auto_version_tool import extract_keypairs
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
                "VERSION": "19.99.0-dev.1",
                "VERSION_AGAIN": "19.99.0-dev.1",
                "STRICT_VERSION": "19.99.0",
            },
        )

    def test_build(self):
        old, new, updates = self.call(bump="build")
        self.assertEqual(
            updates,
            {
                "VERSION": "19.99.0+build.1",
                "VERSION_AGAIN": "19.99.0+build.1",
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


@unittest.skipIf(os.getenv('CI', False), "Running on CI")
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

    def tearDown(self):
        cmd = "git tag --delete release/4.5.6"
        subprocess.check_call(shlex.split(cmd))
        try:
            cmd = "git tag --delete release/5.0.0-dev.1"
            subprocess.check_call(shlex.split(cmd))
        except Exception:
            pass

    def test_from_ancestor_tag(self):
        """i.e. most immediate ancestor tag"""
        bumped = "5.0.0-dev.1"
        old, new, updates = self.call(
            persist_from=[Constants.FROM_VCS_ANCESTOR], bump="major"
        )
        self.assertEqual(
            updates,
            {"VERSION": bumped, "VERSION_AGAIN": bumped, "STRICT_VERSION": "5.0.0"},
        )

    def test_from_latest_of_all_time(self):
        """i.e. latest version tag across the entire repo
        (TODO: but we cant test global tags without making a new branch etc etc)
        """
        bumped = "5.0.0-dev.1"
        old, new, updates = self.call(
            persist_from=[Constants.FROM_VCS_LATEST], bump="major"
        )
        self.assertEqual(
            updates,
            {"VERSION": bumped, "VERSION_AGAIN": bumped, "STRICT_VERSION": "5.0.0"},
        )

    def test_to_tag(self):
        """writes a tag in git
        (TODO: but we cant test global tags without making a new branch etc etc)
        """
        bumped = "5.0.0-dev.1"
        old, new, updates = self.call(
            persist_from=[Constants.FROM_VCS_LATEST],
            persist_to=[Constants.TO_VCS],
            bump="major",
        )
        self.assertEqual(
            updates,
            {"VERSION": bumped, "VERSION_AGAIN": bumped, "STRICT_VERSION": "5.0.0"},
        )
        version = auto_version_tool.get_dvcs_latest_tag_semver()
        self.assertEqual(
            dict(version._asdict()),
            dict(major=5, minor=0, patch=0, build=None, prerelease="dev.1"),
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
        for line in self.lines:
            with self.subTest(line=line) if six.PY3 else Noop():
                extracted = extract_keypairs([line], self.regexer)
                self.assertEqual({self.key: self.value}, extracted)

    def test_non_match(self):
        for line in self.non_matching:
            with self.subTest(line=line) if six.PY3 else Noop():
                extracted = extract_keypairs([line], self.regexer)
                self.assertEqual({}, extracted)

    def test_replace(self):
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
