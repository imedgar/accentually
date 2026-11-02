"""Self-update from GitHub Releases.

Flow: query the latest release, download the installer asset, verify its SHA-256
against the published `<asset>.sha256` file, then run it silently. The installer
replaces the files and relaunches the app.
"""
import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional, Tuple
from urllib.parse import urlparse

from core.version import GITHUB_REPO, INSTALLER_ASSET, __version__

API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
ALLOWED_HOSTS = ("github.com", "githubusercontent.com")
TIMEOUT = 15


class UpdateError(Exception):
    pass


@dataclass
class UpdateInfo:
    version: str
    url: str
    sha256: str
    notes: str


def parse_version(text: str) -> Tuple[int, ...]:
    parts = re.findall(r"\d+", text.split("-")[0])
    return tuple(int(p) for p in parts) or (0,)


def is_newer(candidate: str, current: str = __version__) -> bool:
    return parse_version(candidate) > parse_version(current)


def _check_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or not any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS):
        raise UpdateError(f"Refusing to download from {url}")
    return url


def _get(url: str) -> bytes:
    request = urllib.request.Request(_check_url(url), headers={
        "User-Agent": f"Accentually/{__version__}",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def fetch_latest() -> Optional[UpdateInfo]:
    """Return the latest release, or None if it has no usable installer."""
    try:
        release = json.loads(_get(API_URL))
    except (OSError, ValueError) as exc:  # URLError/HTTPError/timeouts are OSErrors
        raise UpdateError(f"Could not reach GitHub: {exc}") from exc
    assets = {a.get("name"): a.get("browser_download_url") for a in release.get("assets", [])}
    url, sha_url = assets.get(INSTALLER_ASSET), assets.get(INSTALLER_ASSET + ".sha256")
    if not url or not sha_url:
        return None
    try:
        sha = _get(sha_url).decode("ascii", "replace").split()[0].lower()
    except (OSError, IndexError) as exc:
        raise UpdateError(f"Could not fetch checksum: {exc}") from exc
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise UpdateError("Malformed checksum file")
    return UpdateInfo(release.get("tag_name", "").lstrip("vV"), url, sha, release.get("body") or "")


def download(info: UpdateInfo, progress: Optional[Callable[[int, int], None]] = None) -> str:
    """Download the installer to a fresh temp folder and verify its checksum."""
    request = urllib.request.Request(_check_url(info.url), headers={"User-Agent": f"Accentually/{__version__}"})
    path = os.path.join(tempfile.mkdtemp(prefix="accentually-update-"), INSTALLER_ASSET)
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response, open(path, "wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            while chunk := response.read(256 * 1024):
                out.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    except OSError as exc:
        raise UpdateError(f"Download failed: {exc}") from exc
    if digest.hexdigest() != info.sha256:
        os.remove(path)
        raise UpdateError("Checksum mismatch; the download was discarded.")
    return path


def launch_installer(path: str):
    """Start the silent installer detached; the caller must exit right after."""
    subprocess.Popen(
        [path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )
