"""Publish chart archives to GitHub Container Registry using Helm OCI support."""

import os
import re
import subprocess
from pathlib import Path


def can_publish(env):
    if env.get("GITHUB_EVENT_NAME") != "push":
        return False
    if env.get("GITHUB_REF_TYPE") == "tag":
        return True
    return env.get("GITHUB_REF_TYPE") == "branch" and (
        env.get("GITHUB_REF_NAME") == "main"
        or env.get("GITHUB_REF_PROTECTED") == "true"
    )


def publish(directory, env):
    if not can_publish(env):
        raise ValueError("This event/ref is not eligible for chart publication")
    owner = env["GITHUB_REPOSITORY_OWNER"].lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", owner):
        raise ValueError("Invalid GitHub repository owner")
    archives = sorted(directory.glob("octelium-*.tgz"))
    if not archives:
        raise ValueError("No chart archives to publish")
    target = f"oci://ghcr.io/{owner}/charts"
    # The workflow authenticates through helm registry login using GITHUB_TOKEN.
    for archive in archives:
        subprocess.run(["helm", "push", str(archive), target], check=True)


def main():
    publish(Path("dist"), os.environ)


if __name__ == "__main__":
    main()
