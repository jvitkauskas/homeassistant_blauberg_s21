"""Check release metadata against the dependencies actually used by CI."""

import argparse
import json
import re
from importlib.metadata import version
from pathlib import Path

from packaging.requirements import Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parent.parent


def validate_metadata(
    manifest: dict,
    hacs: dict,
    test_requirements: str,
    installed: dict[str, str],
    *,
    ha_channel: str = "minimum",
    tag: str = "",
) -> None:
    """Reject mismatched dependencies, unsupported HA versions, or release tags."""
    integration_version = manifest["version"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", integration_version):
        raise ValueError("The manifest must contain a stable major.minor.patch version")
    if tag and tag != f"v{integration_version}":
        raise ValueError(f"Tag {tag!r} must match v{integration_version}")

    pins = {
        line.strip()
        for line in test_requirements.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    for raw_requirement in manifest["requirements"]:
        requirement = Requirement(raw_requirement)
        if raw_requirement not in pins:
            raise ValueError(f"Test dependency must match manifest: {raw_requirement}")
        if installed[requirement.name] not in requirement.specifier:
            raise ValueError(f"Installed dependency does not match {raw_requirement}")

    minimum = Version(hacs["homeassistant"])
    actual = Version(installed["homeassistant"])
    if actual < minimum or (ha_channel == "minimum" and actual != minimum):
        raise ValueError(
            f"HA {actual} does not match the {ha_channel} baseline of {minimum}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ha-channel", choices=("minimum", "latest"), default="minimum"
    )
    parser.add_argument("--tag", default="")
    args = parser.parse_args()
    manifest = json.loads(
        (ROOT / "custom_components/blauberg_s21/manifest.json").read_text()
    )
    hacs = json.loads((ROOT / "hacs.json").read_text())
    names = [Requirement(item).name for item in manifest["requirements"]]
    names.extend(["homeassistant", "pytest-homeassistant-custom-component"])
    installed = {name: version(name) for name in names}
    validate_metadata(
        manifest,
        hacs,
        (ROOT / "requirements-common.txt").read_text(),
        installed,
        ha_channel=args.ha_channel,
        tag=args.tag,
    )
    print(f"Integration: {manifest['version']}; tag: {args.tag or '(not releasing)'}")
    for name, installed_version in installed.items():
        print(f"{name}=={installed_version}")


if __name__ == "__main__":
    main()
