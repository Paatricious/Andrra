import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

import convert


def make_source_image(width=600, height=900):
    """A colorful RGB image larger than the target so ImageOps.fit crops."""
    img = Image.new("RGB", (width, height))
    px = img.load()
    for y in range(height):
        for x in range(width):
            px[x, y] = ((x * 255) // width, (y * 255) // height, (x + y) % 256)
    return img


class ConvertImageTest(unittest.TestCase):
    def test_artifacts_are_480x800_and_right_modes(self):
        entry = {"id": "test-001", "source_url": "https://example.invalid/x.jpg"}
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bw = tmp / "bw.bmp"
            gray = tmp / "gray.bmp"
            thumb = tmp / "thumb.png"

            # Stub fetch_bytes so no network is needed.
            buf = io.BytesIO()
            make_source_image().save(buf, format="JPEG")
            original_fetch = convert.fetch_bytes
            convert.fetch_bytes = lambda url: buf.getvalue()
            try:
                digest = convert.convert_image(entry, bw, gray, thumb)
            finally:
                convert.fetch_bytes = original_fetch

            self.assertEqual(len(digest), 64)  # sha256 hex

            with Image.open(bw) as im:
                self.assertEqual(im.size, (convert.SCREEN_W, convert.SCREEN_H))
                self.assertEqual(im.mode, "1")
            with Image.open(gray) as im:
                self.assertEqual(im.size, (convert.SCREEN_W, convert.SCREEN_H))
                self.assertEqual(im.mode, "L")
            with Image.open(thumb) as im:
                self.assertEqual(im.size, (convert.THUMB_W, convert.THUMB_H))

    def test_catalog_entry_shape(self):
        entry = {
            "id": "wm-aurora-001", "title": "Aurora", "author": "A",
            "license": "CC0", "attribution": "", "category": "landscape",
        }
        got = convert.catalog_entry(entry)
        self.assertEqual(
            got,
            {
                "id": "wm-aurora-001", "title": "Aurora", "short_title": "Aurora",
                "author": "A",
                "license": "CC0", "attribution": "", "category": "landscape",
                "bw": "wallpapers/bw/wm-aurora-001.bmp",
                "gray": "wallpapers/gray/wm-aurora-001.bmp",
                "thumb": "wallpapers/thumbs/wm-aurora-001.png",
            },
        )

    def test_short_title_truncates_at_word_boundary(self):
        long_title = "A photograph made from a B-17 Flying Fortress attacking the CAM ball-bearing plant in Paris."
        self.assertEqual(
            convert._short_title(long_title),
            "A photograph made from a B-17…",
        )
        self.assertLessEqual(len(convert._short_title(long_title)), 33)
        self.assertEqual(convert._short_title("Short title"), "Short title")


class ValidateEntryTest(unittest.TestCase):
    def test_valid_entry_passes(self):
        entry = {
            "id": "wm-aurora-001", "title": "Aurora", "author": "A",
            "license": "CC BY-SA 4.0", "attribution": "© A",
            "source": "https://commons.wikimedia.org/wiki/File:X.jpg",
            "source_url": "https://upload.wikimedia.org/x.jpg",
        }
        self.assertEqual(convert.validate_entry(entry), entry)

    def test_bad_id_rejected(self):
        entry = dict(self.valid(), id="Has Space/../evil")
        with self.assertRaises(ValueError):
            convert.validate_entry(entry)

    def test_disallowed_license_rejected(self):
        entry = dict(self.valid(), license="All Rights Reserved")
        with self.assertRaises(ValueError):
            convert.validate_entry(entry)

    def test_cc_by_requires_attribution(self):
        entry = dict(self.valid(), license="CC BY", attribution="")
        with self.assertRaises(ValueError):
            convert.validate_entry(entry)

    def test_cc_by_40_passes(self):
        entry = dict(self.valid(), license="CC BY 4.0", attribution="© A")
        self.assertEqual(convert.validate_entry(entry), entry)

    def test_public_domain_lowercase_passes(self):
        entry = dict(self.valid(), license="Public domain", attribution="© Author")
        self.assertEqual(convert.validate_entry(entry), entry)

    @staticmethod
    def valid():
        return {
            "id": "wm-aurora-001", "title": "Aurora", "author": "A",
            "license": "CC BY-SA 4.0", "attribution": "© A",
            "source": "https://commons.wikimedia.org/wiki/File:X.jpg",
            "source_url": "https://upload.wikimedia.org/x.jpg",
        }


class SourcesAndCatalogTest(unittest.TestCase):
    def test_convert_sources_skips_existing_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            # Pre-create artifacts so the entry counts as already converted.
            (tmp / "bw").mkdir(parents=True)
            (tmp / "gray").mkdir()
            (tmp / "thumbs").mkdir()
            for d in ("bw", "gray"):
                Image.new("1", (convert.SCREEN_W, convert.SCREEN_H)).save(
                    tmp / d / "wm-aurora-001.bmp", format="BMP")
            Image.new("L", (convert.THUMB_W, convert.THUMB_H)).save(
                tmp / "thumbs" / "wm-aurora-001.png", format="PNG")

            original_dirs = (convert.BW_DIR, convert.GRAY_DIR, convert.THUMB_DIR)
            convert.BW_DIR, convert.GRAY_DIR, convert.THUMB_DIR = (
                tmp / "bw", tmp / "gray", tmp / "thumbs")
            try:
                entries = convert.convert_sources([ValidateEntryTest.valid()], force=False)
            finally:
                convert.BW_DIR, convert.GRAY_DIR, convert.THUMB_DIR = original_dirs

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["id"], "wm-aurora-001")

    def test_write_catalog_and_third_party(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cat = tmp / "wallpapers.json"
            tp = tmp / "THIRD_PARTY.md"
            entries = [convert.catalog_entry(ValidateEntryTest.valid())]
            convert.write_catalog(entries, path=cat)
            convert.write_third_party([ValidateEntryTest.valid()], path=tp)

            data = json.loads(cat.read_text(encoding="utf-8"))
            self.assertEqual(data["name"], "Andrra")
            self.assertEqual(data["wallpapers"][0]["id"], "wm-aurora-001")
            self.assertIn("CC BY-SA 4.0", tp.read_text(encoding="utf-8"))
            self.assertIn("https://commons.wikimedia.org/wiki/File:X.jpg", tp.read_text(encoding="utf-8"))

    def test_third_party_escapes_pipes_and_newlines_in_cells(self):
        entry = dict(ValidateEntryTest.valid(), id="wm-pipe-001",
                     title="B-17 bomber\nLeft | Right wing")
        with tempfile.TemporaryDirectory() as tmp:
            tp = Path(tmp) / "THIRD_PARTY.md"
            convert.write_third_party([entry], path=tp)
            lines = tp.read_text(encoding="utf-8").splitlines()
            rows = lines[lines.index("|---|---|---|---|---|") + 1:]
            self.assertEqual(len(rows), 1)  # the newline in title must not split the row
            self.assertIn(r"Left \| Right wing", rows[0])  # pipe escaped inside the cell
            cells = [c for c in re.split(r"(?<!\\)\|", rows[0]) if c.strip()]
            self.assertEqual(len(cells), 5)  # exactly 5 pipe-separated columns


class CliTest(unittest.TestCase):
    def test_convert_cli_converts_and_writes_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "bw").mkdir(parents=True)
            (tmp / "gray").mkdir()
            (tmp / "thumbs").mkdir()
            src = tmp / "sources.json"
            src.write_text(json.dumps({"wallpapers": [ValidateEntryTest.valid()]}), encoding="utf-8")
            cat = tmp / "wallpapers.json"
            tp = tmp / "THIRD_PARTY.md"

            buf = io.BytesIO()
            Image.new("RGB", (600, 900)).save(buf, format="JPEG")
            original = (convert.SOURCES_PATH, convert.CATALOG_PATH, convert.THIRD_PARTY_PATH,
                        convert.BW_DIR, convert.GRAY_DIR, convert.THUMB_DIR, convert.fetch_bytes)
            (convert.SOURCES_PATH, convert.CATALOG_PATH, convert.THIRD_PARTY_PATH,
             convert.BW_DIR, convert.GRAY_DIR, convert.THUMB_DIR) = (
                src, cat, tp, tmp / "bw", tmp / "gray", tmp / "thumbs")
            convert.fetch_bytes = lambda url: buf.getvalue()
            try:
                rc = convert.main(["convert"])
            finally:
                (convert.SOURCES_PATH, convert.CATALOG_PATH, convert.THIRD_PARTY_PATH,
                 convert.BW_DIR, convert.GRAY_DIR, convert.THUMB_DIR, convert.fetch_bytes) = original

            self.assertEqual(rc, 0)
            data = json.loads(cat.read_text(encoding="utf-8"))
            self.assertEqual(data["wallpapers"][0]["id"], "wm-aurora-001")
            self.assertTrue((tmp / "bw" / "wm-aurora-001.bmp").exists())


class _FakeResp:
    def read(self):
        return b"fake-image-bytes"


class _FakeCM:
    def __enter__(self):
        return _FakeResp()

    def __exit__(self, *args):
        return False


class FetchBytesTest(unittest.TestCase):
    def test_fetch_bytes_sends_descriptive_user_agent(self):
        with mock.patch("convert.urlopen", return_value=_FakeCM()) as uo:
            data = convert.fetch_bytes("https://example.invalid/x.jpg")

        uo.assert_called_once()
        req = uo.call_args.args[0]
        self.assertIn("Andrra", req.get_header("User-agent"))
        self.assertEqual(data, b"fake-image-bytes")


if __name__ == "__main__":
    unittest.main()
