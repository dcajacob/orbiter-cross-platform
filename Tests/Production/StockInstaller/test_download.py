"""Exercise the installer cache with simulated HTTP responses."""
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "Utils/StockDataInstaller"))
from installer import download

CONTENT = b"checksum-locked contents of an archive"
RECORD = dict(url="https://example.com/archive.zip", bytes=len(CONTENT),
              sha256=hashlib.sha256(CONTENT).hexdigest())


def response(body, status, headers=None):
    stream = io.BytesIO(body)
    stream.status = status
    stream.headers = headers or {}
    return stream


class DownloadTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.archive = Path(self.directory.name) / "archive.zip"
        self.partial = self.archive.with_suffix(".zip.partial")

    def test_short_download_is_resumed(self):
        offset = 12
        with patch("urllib.request.urlopen", return_value=response(CONTENT[:offset], 200)):
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                download(self.archive, RECORD, False)
        self.assertEqual(self.partial.read_bytes(), CONTENT[:offset])
        self.assertFalse(self.archive.exists())
        remaining = response(CONTENT[offset:], 206,
                             {"Content-Range": f"bytes {offset}-{len(CONTENT) - 1}/{len(CONTENT)}"})
        with patch("urllib.request.urlopen", return_value=remaining) as fetch:
            download(self.archive, RECORD, False)
        self.assertEqual(fetch.call_args.args[0].get_header("Range"), f"bytes={offset}-")
        self.assertEqual(self.archive.read_bytes(), CONTENT)
        self.assertFalse(self.partial.exists())

    def test_server_full_response_replaces_partial(self):
        self.partial.write_bytes(CONTENT[:12])
        with patch("urllib.request.urlopen", return_value=response(CONTENT, 200)):
            download(self.archive, RECORD, False)
        self.assertEqual(self.archive.read_bytes(), CONTENT)

    def test_wrong_range_keeps_partial(self):
        self.partial.write_bytes(CONTENT[:12])
        bad = response(CONTENT[8:], 206, {"Content-Range": f"bytes 8-{len(CONTENT) - 1}/{len(CONTENT)}"})
        with patch("urllib.request.urlopen", return_value=bad):
            with self.assertRaisesRegex(ValueError, "Unexpected Content-Range"):
                download(self.archive, RECORD, False)
        self.assertEqual(self.partial.read_bytes(), CONTENT[:12])
        self.assertFalse(self.archive.exists())

    def test_offline_accepts_only_verified_cache(self):
        with patch("urllib.request.urlopen") as fetch:
            with self.assertRaisesRegex(ValueError, "Offline cache is missing"):
                download(self.archive, RECORD, True)
            self.archive.write_bytes(CONTENT)
            self.assertEqual(download(self.archive, RECORD, True), self.archive)
            self.archive.write_bytes(CONTENT[::-1])
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                download(self.archive, RECORD, True)
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
