"""Package standalone charts, with release metadata changed only in a temporary copy."""

import argparse
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def package_version(base, env):
    tag = (
        env.get("GITHUB_REF_NAME", "")
        if env.get("GITHUB_EVENT_NAME") == "push"
        and env.get("GITHUB_REF_TYPE") == "tag"
        else ""
    )
    if tag:
        version = tag.removeprefix("v")
    elif env.get("GITHUB_RUN_ID"):
        version = f"{base}-dev.{env['GITHUB_RUN_ID']}"
    else:
        version = base
    if not SEMVER.fullmatch(version):
        raise ValueError(f"Chart version must be semantic versioning: {version}")
    return version


def package(destination, version=None):
    destination.mkdir(parents=True, exist_ok=True)
    common = yaml.safe_load((ROOT / "charts/octelium-common/Chart.yaml").read_text())
    version = version or package_version(common["version"], os.environ)
    if not SEMVER.fullmatch(version):
        raise ValueError(f"Invalid chart version: {version}")
    with tempfile.TemporaryDirectory() as directory:
        charts = Path(directory) / "charts"
        shutil.copytree(
            ROOT / "charts",
            charts,
            ignore=shutil.ignore_patterns(
                "*.tgz", ".git", ".aws", ".codex", ".agents", ".DS_Store"
            ),
        )
        for chart in sorted(charts.iterdir()):
            metadata = yaml.safe_load((chart / "Chart.yaml").read_text())
            metadata["version"] = version
            for dependency in metadata.get("dependencies", []):
                dependency["version"] = version
            (chart / "Chart.yaml").write_text(yaml.safe_dump(metadata, sort_keys=False))
        for chart in sorted(charts.iterdir()):
            metadata = yaml.safe_load((chart / "Chart.yaml").read_text())
            if metadata.get("dependencies"):
                subprocess.run(
                    ["helm", "dependency", "update", "--skip-refresh", str(chart)],
                    check=True,
                )
            subprocess.run(
                [
                    "helm",
                    "package",
                    str(chart),
                    "--destination",
                    str(destination.resolve()),
                ],
                check=True,
            )
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=Path("dist"))
    parser.add_argument("--version")
    arguments = parser.parse_args()
    package(arguments.destination, arguments.version)


if __name__ == "__main__":
    main()
