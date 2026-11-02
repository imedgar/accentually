"""Checks for version comparison, release parsing and download verification."""
import hashlib
import io
import json
import os
import unittest
from unittest.mock import patch

from core import updater
from core.version import INSTALLER_ASSET

GOOD_URL = "https://github.com/imedgar/accentually/releases/download/v9.9.9/" + INSTALLER_ASSET


class FakeResponse(io.BytesIO):
    headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class VersionTests(unittest.TestCase):
    def test_numeric_not_lexicographic_comparison(self):
        self.assertTrue(updater.is_newer("1.10.0", "1.9.0"))
        self.assertTrue(updater.is_newer("v2.0", "1.9.9"))
        self.assertFalse(updater.is_newer("1.0.0", "1.0.0"))
        self.assertFalse(updater.is_newer("0.9.9", "1.0.0"))

    def test_prerelease_suffix_is_ignored(self):
        self.assertEqual(updater.parse_version("v1.2.3-beta"), (1, 2, 3))


class ReleaseTests(unittest.TestCase):
    def _release(self, assets):
        return json.dumps({"tag_name": "v9.9.9", "body": "notes", "assets": assets}).encode()

    def test_release_with_installer_and_checksum(self):
        sha = "a" * 64
        assets = [
            {"name": INSTALLER_ASSET, "browser_download_url": GOOD_URL},
            {"name": INSTALLER_ASSET + ".sha256", "browser_download_url": GOOD_URL + ".sha256"},
        ]
        with patch("core.updater._get", side_effect=[self._release(assets), f"{sha}  {INSTALLER_ASSET}".encode()]):
            info = updater.fetch_latest()
        self.assertEqual((info.version, info.sha256, info.url), ("9.9.9", sha, GOOD_URL))

    def test_release_without_checksum_is_ignored(self):
        assets = [{"name": INSTALLER_ASSET, "browser_download_url": GOOD_URL}]
        with patch("core.updater._get", return_value=self._release(assets)):
            self.assertIsNone(updater.fetch_latest())

    def test_malformed_checksum_is_rejected(self):
        assets = [
            {"name": INSTALLER_ASSET, "browser_download_url": GOOD_URL},
            {"name": INSTALLER_ASSET + ".sha256", "browser_download_url": GOOD_URL + ".sha256"},
        ]
        with patch("core.updater._get", side_effect=[self._release(assets), b"not-a-hash"]):
            with self.assertRaises(updater.UpdateError):
                updater.fetch_latest()


class DownloadTests(unittest.TestCase):
    def test_only_https_github_hosts_are_allowed(self):
        for url in ("http://github.com/x", "https://evil.example/x", "https://github.com.evil.example/x"):
            with self.assertRaises(updater.UpdateError):
                updater._check_url(url)
        updater._check_url("https://objects.githubusercontent.com/x")

    def test_checksum_mismatch_discards_download(self):
        info = updater.UpdateInfo("9.9.9", GOOD_URL, "0" * 64, "")
        with patch("core.updater.urllib.request.urlopen", return_value=FakeResponse(b"payload")):
            with self.assertRaises(updater.UpdateError):
                updater.download(info)

    def test_matching_checksum_returns_path(self):
        payload = b"payload"
        info = updater.UpdateInfo("9.9.9", GOOD_URL, hashlib.sha256(payload).hexdigest(), "")
        with patch("core.updater.urllib.request.urlopen", return_value=FakeResponse(payload)):
            path = updater.download(info)
        self.addCleanup(os.rmdir, os.path.dirname(path))
        self.addCleanup(os.remove, path)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), payload)


if __name__ == "__main__":
    unittest.main()
