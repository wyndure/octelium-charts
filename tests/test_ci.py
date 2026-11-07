"""Version selection and GitHub OCI chart publication checks."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ci.package_charts import package_version
from ci.publish_charts import can_publish, publish


def event(
    ref_type="branch", name="main", protected="false", run_id="123", event_name="push"
):
    return {
        "GITHUB_EVENT_NAME": event_name,
        "GITHUB_REF_TYPE": ref_type,
        "GITHUB_REF_NAME": name,
        "GITHUB_REF_PROTECTED": protected,
        "GITHUB_RUN_ID": run_id,
        "GITHUB_REPOSITORY_OWNER": "Wyndure",
    }


class ReleasePolicyTest(unittest.TestCase):
    def test_versions_and_publication(self):
        for env, expected_version, eligible in [
            ({}, "0.49.0", False),
            (event(), "0.49.0-dev.123", True),
            (event(name="release/next", protected="true"), "0.49.0-dev.123", True),
            (event(name="feature"), "0.49.0-dev.123", False),
            (event(ref_type="tag", name="v1.2.3"), "1.2.3", True),
            (event(ref_type="tag", name="1.2.3-rc.1"), "1.2.3-rc.1", True),
            (
                event(event_name="pull_request", protected="true"),
                "0.49.0-dev.123",
                False,
            ),
            (
                event(ref_type="tag", name="v1.2.3", event_name="pull_request"),
                "0.49.0-dev.123",
                False,
            ),
        ]:
            with self.subTest(env=env):
                self.assertEqual(package_version("0.49.0", env), expected_version)
                self.assertEqual(can_publish(env), eligible)

    def test_invalid_versions(self):
        for version in ["invalid", "1.2", "01.2.3", "1.2.3-dev.01", "1.2.3/path"]:
            with self.subTest(version=version):
                with self.assertRaises(ValueError):
                    package_version("0.49.0", event(ref_type="tag", name=version))

    @patch("ci.publish_charts.subprocess.run")
    def test_oci_upload(self, run):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            archive = path / "octelium-example-1.2.3.tgz"
            archive.write_bytes(b"chart-bytes")
            publish(path, event(ref_type="tag", name="v1.2.3"))
            run.assert_called_once_with(
                ["helm", "push", str(archive), "oci://ghcr.io/wyndure/charts"],
                check=True,
            )

    @patch("ci.publish_charts.subprocess.run")
    def test_pull_requests_cannot_upload(self, run):
        with self.assertRaises(ValueError):
            publish(Path("dist"), event(event_name="pull_request", protected="true"))
        run.assert_not_called()
