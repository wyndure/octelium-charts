"""Install the pinned Helm CLI into .tools, verifying its release checksum."""

import hashlib
import io
import platform
import tarfile
import urllib.request
from pathlib import Path

VERSION = "3.19.0"
CHECKSUMS = {
    "amd64": "a7f81ce08007091b86d8bd696eb4d86b8d0f2e1b9f6c714be62f82f96a594496",
    "arm64": "440cf7add0aee27ebc93fada965523c1dc2e0ab340d4348da2215737fc0d76ad",
}


def main():
    arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine())
    if platform.system() != "Linux" or arch is None:
        raise SystemExit("Install Helm 3.19.0 manually on this platform")
    url = f"https://get.helm.sh/helm-v{VERSION}-linux-{arch}.tar.gz"
    with urllib.request.urlopen(url, timeout=60) as response:
        content = response.read()
    if hashlib.sha256(content).hexdigest() != CHECKSUMS[arch]:
        raise SystemExit("Helm archive checksum verification failed")
    with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as archive:
        binary = archive.extractfile(f"linux-{arch}/helm").read()
    target = Path(".tools/helm")
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(binary)
    target.chmod(0o755)
    print(f"Installed Helm {VERSION} for linux/{arch}")


if __name__ == "__main__":
    main()
