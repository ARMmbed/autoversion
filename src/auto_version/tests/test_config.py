import json
import os
import unittest

from auto_version import config


class TestConfig(unittest.TestCase):
    """the config system is a bit dubious because it's all module-level ..."""

    def setUp(self) -> None:
        self.before = json.dumps(config.AutoVersionConfig._deflate())

    def tearDown(self) -> None:
        config.AutoVersionConfig._inflate(json.loads(self.before))

    def test_load_tool_file(self):
        config.get_or_create_config(
            path=os.path.join(os.path.dirname(__file__), "example_tool.toml"),
            config=config.AutoVersionConfig,
        )
        self.assertEqual(config.AutoVersionConfig.targets, ["banana.py"])
        self.assertEqual(config.AutoVersionConfig.CONFIG_NAME, "tool")

    def test_load_legacy_file(self):
        config.get_or_create_config(
            path=os.path.join(os.path.dirname(__file__), "example.toml"),
            config=config.AutoVersionConfig,
        )
        self.assertEqual(config.AutoVersionConfig.targets, ["example.py"])
        self.assertEqual(config.AutoVersionConfig.CONFIG_NAME, "example")

    def test_default_create_file(self):
        path = os.path.join(os.path.dirname(__file__), "example_create.toml")
        try:
            os.remove(path)
        except OSError:
            pass
        config.get_or_create_config(path=path, config=config.AutoVersionConfig)
        self.assertEqual(
            config.AutoVersionConfig.targets,
            [os.path.join("path", "to", "source", "code")],
        )
        self.assertEqual(config.AutoVersionConfig.CONFIG_NAME, "an example config")
