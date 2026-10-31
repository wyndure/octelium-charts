"""Build local dependencies and strictly lint every chart."""

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    for chart in sorted((ROOT / "charts").iterdir()):
        metadata = yaml.safe_load((chart / "Chart.yaml").read_text())
        if metadata.get("dependencies"):
            subprocess.run(
                ["helm", "dependency", "build", "--skip-refresh", str(chart)],
                check=True,
            )
        args = ["helm", "lint", "--strict", str(chart)]
        if chart.name == "octelium-rscserver":
            args += ["-f", str(ROOT / "examples/rscserver.yaml")]
        subprocess.run(args, check=True)


if __name__ == "__main__":
    main()
