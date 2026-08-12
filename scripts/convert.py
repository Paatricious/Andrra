"""Wallpaper conversion pipeline for Andrra (sleep-screen wallpapers for
CrossPoint e-readers).

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
from urllib.request import Request, urlopen

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
    req = Request(url, headers={
        "User-Agent": "Andrra/1.0 (https://github.com/Paatricious/Andrra; sleep-screen wallpaper store)",
    })
    with urlopen(req, timeout=60) as resp:
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
    required = ("id", "title", "author", "license", "attribution", "source", "source_url")
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
    data = {"name": "Andrra", "wallpapers": sorted(entries, key=lambda e: e["id"])}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _md_cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


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
        cells = [_md_cell(e[k]) for k in ("id", "title", "license", "attribution", "source")]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def merge_candidates(candidates, sources):
    """Add puller candidates that aren't already in sources (by id)."""
    existing = {e["id"] for e in sources}
    added = []
    for cand in candidates:
        if cand["id"] in existing:
            continue
        try:
            validate_entry(cand)
        except ValueError as exc:
            print(f"SKIP candidate {cand.get('id')}: {exc}", file=sys.stderr)
            continue
        sources.append(cand)
        existing.add(cand["id"])
        added.append(cand["id"])
    return added


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pull = sub.add_parser("pull", help="merge new candidates into sources.json")
    pull.add_argument("--limit", type=int, default=20)
    convert_p = sub.add_parser("convert", help="convert sources without artifacts")
    convert_p.add_argument("--force", action="store_true")
    convert_p.add_argument("--entry", help="convert only this entry id")
    sub.add_parser("update", parents=[convert_p], add_help=False, help="alias of convert")
    cli = parser.parse_args(args)

    if cli.command == "pull":
        from pullers import wikimedia
        sources = load_sources(SOURCES_PATH)
        candidates = wikimedia.featured_pictures(limit=cli.limit)
        added = merge_candidates(candidates, sources)
        SOURCES_PATH.write_text(
            json.dumps({"wallpapers": sources}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        print(f"pull: {len(added)} new candidate(s) added")
        return 0

    sources = load_sources(SOURCES_PATH)
    if cli.entry:
        sources = [e for e in sources if e["id"] == cli.entry]
    entries = convert_sources(sources, force=cli.force)
    write_catalog(entries, CATALOG_PATH)
    write_third_party(sources, THIRD_PARTY_PATH)
    print(f"convert: {len(entries)} wallpaper(s) in catalog")
    return 0


if __name__ == "__main__":
    sys.exit(main())
