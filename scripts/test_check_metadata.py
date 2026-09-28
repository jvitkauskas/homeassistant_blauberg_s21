"""Regression tests for CI and release rejection paths; no Home Assistant needed."""

import unittest

from check_metadata import validate_metadata


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {"version": "0.6.0", "requirements": ["pybls21==5.2.0"]}
        self.hacs = {"homeassistant": "2026.9.4"}
        self.requirements = "# Shared requirements\npybls21==5.2.0\nruff>=0.14\n"
        self.installed = {"homeassistant": "2026.9.4", "pybls21": "5.2.0"}

    def validate(self, **kwargs):
        validate_metadata(
            self.manifest, self.hacs, self.requirements, self.installed, **kwargs
        )

    def test_baseline_and_matching_release(self):
        self.validate()
        self.validate(tag="v0.6.0")

    def test_wrong_release_tag(self):
        for tag in ("v0.5.0", "0.6.0", "v0.6.0-rc1", "v0.6.0\n"):
            with self.subTest(tag=tag), self.assertRaisesRegex(ValueError, "Tag"):
                self.validate(tag=tag)

    def test_invalid_manifest_version(self):
        self.manifest["version"] = "0.6.0b1"
        with self.assertRaisesRegex(ValueError, "stable"):
            self.validate()

    def test_missing_or_different_test_dependency(self):
        for requirements in ("", "pybls21==5.1.0", "pybls21>=5.2.0"):
            self.requirements = requirements
            with self.subTest(requirements=requirements):
                with self.assertRaisesRegex(ValueError, "Test dependency"):
                    self.validate()

    def test_incorrect_installed_library(self):
        self.installed["pybls21"] = "5.1.0"
        with self.assertRaisesRegex(ValueError, "Installed dependency"):
            self.validate()

    def test_baseline_must_match_declared_minimum(self):
        self.installed["homeassistant"] = "2026.10.0"
        with self.assertRaisesRegex(ValueError, "baseline"):
            self.validate()

    def test_compatibility_allows_same_or_newer_ha(self):
        self.validate(ha_channel="latest")
        self.installed["homeassistant"] = "2026.10.0"
        self.validate(ha_channel="latest")

    def test_compatibility_rejects_older_ha(self):
        self.installed["homeassistant"] = "2026.9.3"
        with self.assertRaisesRegex(ValueError, "baseline"):
            self.validate(ha_channel="latest")


if __name__ == "__main__":
    unittest.main()
