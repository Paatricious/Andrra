import io
import tempfile
import unittest
from pathlib import Path

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
                "id": "wm-aurora-001", "title": "Aurora", "author": "A",
                "license": "CC0", "attribution": "", "category": "landscape",
                "bw": "wallpapers/bw/wm-aurora-001.bmp",
                "gray": "wallpapers/gray/wm-aurora-001.bmp",
                "thumb": "wallpapers/thumbs/wm-aurora-001.png",
            },
        )


if __name__ == "__main__":
    unittest.main()
