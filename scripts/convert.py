"""Wallpaper conversion pipeline for the X4 Wallpaper Store.

Converts open-license images into the e-ink BMP formats the CrossPoint
firmware's Bitmap parser accepts:
  - 1-bit dithered BMP (mode '1')  -> hasGreyscale()==False, plain display
  - 8-bit grayscale BMP (mode 'L') -> hasGreyscale()==True, grayscale pipeline
Both are exactly 480x800 (center-crop cover), BI_RGB, which parseHeaders
accepts (bpp 1/2/4/8/24/32, compression 0).
"""

import argparse
import hashlib
import io
import json
import re
import sys
from pathlib import Path
from urllib.request import urlopen

from PIL import Image, ImageOps

SCREEN_W, SCREEN_H = 480, 800
THUMB_W, THUMB_H = 120, 200
ALLOWED_LICENSES = {"CC0", "CC BY", "CC BY-SA", "CC BY 3.0", "CC BY-SA 3.0", "CC BY 4.0", "CC BY-SA 4.0", "Public Domain", "Public domain"}

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = REPO_ROOT / "sources.json"
CATALOG_PATH = REPO_ROOT / "wallpapers.json"
THIRD_PARTY_PATH = REPO_ROOT / "THIRD_PARTY.md"
BW_DIR = REPO_ROOT / "wallpapers" / "bw"
GRAY_DIR = REPO_ROOT / "wallpapers" / "gray"
THUMB_DIR = REPO_ROOT / "wallpapers" / "thumbs"


def fetch_bytes(url):
    with urlopen(url, timeout=60) as resp:
        return resp.read()


def convert_image(entry, out_bw, out_gray, out_thumb):
    """Download entry['source_url'], convert to the three artifacts.

    Returns the sha256 hex digest of the source bytes (used for dedup).
    """
    data = fetch_bytes(entry["source_url"])
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)
    img = ImageOps.fit(img, (SCREEN_W, SCREEN_H), method=Image.Resampling.LANCZOS)

    img.convert("L").convert("1", dither=Image.Dither.FLOYDSTEINBERG).save(out_bw, format="BMP")
    img.convert("L").save(out_gray, format="BMP")
    img.convert("L").resize((THUMB_W, THUMB_H), Image.Resampling.LANCZOS).save(out_thumb, format="PNG")
    return hashlib.sha256(data).hexdigest()


def catalog_entry(entry):
    return {
        "id": entry["id"],
        "title": entry["title"],
        "author": entry["author"],
        "license": entry["license"],
        "attribution": entry["attribution"],
        "category": entry.get("category", "general"),
        "bw": f"wallpapers/bw/{entry['id']}.bmp",
        "gray": f"wallpapers/gray/{entry['id']}.bmp",
        "thumb": f"wallpapers/thumbs/{entry['id']}.png",
    }


def validate_entry(entry):
    required = ("id", "title", "author", "license", "source", "source_url")
    missing = [k for k in required if not entry.get(k)]
    if missing:
        raise ValueError(f"entry {entry.get('id', '?')}: missing required fields: {missing}")
    if not re.fullmatch(r"[a-z0-9-]+", entry["id"]):
        raise ValueError(f"entry {entry['id']}: id must match ^[a-z0-9-]+$")
    if entry["license"] not in ALLOWED_LICENSES:
        raise ValueError(
            f"entry {entry['id']}: license {entry['license']!r} not allowed "
            f"(allowlist: {sorted(ALLOWED_LICENSES)})")
    if entry["license"].startswith("CC BY") and not entry["attribution"].strip():
        raise ValueError(f"entry {entry['id']}: {entry['license']} requires attribution")
    return entry


def load_sources(path=SOURCES_PATH):
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [validate_entry(e) for e in data.get("wallpapers", [])]


def artifacts_exist(entry):
    return all(p.exists() for p in (
        BW_DIR / f"{entry['id']}.bmp",
        GRAY_DIR / f"{entry['id']}.bmp",
        THUMB_DIR / f"{entry['id']}.png",
    ))


def convert_sources(sources, force=False):
    BW_DIR.mkdir(parents=True, exist_ok=True)
    GRAY_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    for entry in sources:
        if not force and artifacts_exist(entry):
            entries.append(catalog_entry(entry))
            continue
        print(f"converting {entry['id']} …")
        try:
            convert_image(entry, BW_DIR / f"{entry['id']}.bmp",
                          GRAY_DIR / f"{entry['id']}.bmp",
                          THUMB_DIR / f"{entry['id']}.png")
        except Exception as exc:  # one bad image must not kill the run
            print(f"SKIP {entry['id']}: {exc}", file=sys.stderr)
            continue
        entries.append(catalog_entry(entry))
    return entries


def write_catalog(entries, path=CATALOG_PATH):
    data = {"name": "X4 Wallpaper Store", "wallpapers": sorted(entries, key=lambda e: e["id"])}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_third_party(sources, path=THIRD_PARTY_PATH):
    lines = [
        "# Third-party content",
        "",
        "Every wallpaper in this store is open-licensed. Source and attribution:",
        "",
        "| id | title | license | attribution | source |",
        "|---|---|---|---|---|",
    ]
    for e in sorted(sources, key=lambda e: e["id"]):
        lines.append(f"| {e['id']} | {e['title']} | {e['license']} | {e['attribution']} | {e['source']} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", help="convert only this entry id")
    parser.add_argument("--force", action="store_true", help="re-convert even if artifacts exist")
    parser.parse_args(args)
    print("convert core ready; catalog/sources wiring lands in Task 6")
    return 0


if __name__ == "__main__":
    sys.exit(main())
