"""Ensure published archives contain the local library and render independently."""

import subprocess
import tarfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class PackagesTest(unittest.TestCase):
    def test_archives_are_self_contained(self):
        archives = sorted((ROOT / "dist").glob("octelium-*.tgz"))
        if not archives:
            self.skipTest("Run make package to validate chart archives")
        self.assertEqual(len(archives), 7)
        for archive in archives:
            with self.subTest(archive=archive.name), tarfile.open(archive) as tar:
                root_meta = next(
                    m
                    for m in tar
                    if m.name.count("/") == 1 and m.name.endswith("/Chart.yaml")
                )
                metadata = yaml.safe_load(tar.extractfile(root_meta).read())
                if metadata["type"] == "library":
                    continue
                library = next(
                    m
                    for m in tar.getmembers()
                    if m.name.endswith("/charts/octelium-common/Chart.yaml")
                )
                dependency = yaml.safe_load(tar.extractfile(library).read())
                self.assertEqual(
                    dependency["version"], metadata["dependencies"][0]["version"]
                )
                args = ["helm", "template", "packaged", str(archive)]
                if metadata["name"] == "octelium-rscserver":
                    args += ["-f", str(ROOT / "examples/rscserver.yaml")]
                result = subprocess.run(args, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
