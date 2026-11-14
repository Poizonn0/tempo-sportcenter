"""Fetch an official, checksum-verified portable Node.js runtime for Wrangler."""

from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile


VERSION = "v24.11.0"
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "tools" / "node-portable"
ARCHIVE_NAME = f"node-{VERSION}-win-x64.zip"
BASE_URL = f"https://nodejs.org/dist/{VERSION}"


def download(url: str) -> bytes:
    with urlopen(url, timeout=60) as response:
        return response.read()


checksums = download(f"{BASE_URL}/SHASUMS256.txt").decode("ascii")
expected = next(
    line.split()[0]
    for line in checksums.splitlines()
    if line.split()[-1] == ARCHIVE_NAME
)
archive = download(f"{BASE_URL}/{ARCHIVE_NAME}")
actual = sha256(archive).hexdigest()
if actual != expected:
    raise SystemExit("Official Node.js archive checksum did not match.")

DEST.mkdir(parents=True, exist_ok=True)
with ZipFile(__import__("io").BytesIO(archive)) as bundle:
    bundle.extractall(DEST)
print(f"Verified Node.js {VERSION} and extracted it to {DEST}.")
