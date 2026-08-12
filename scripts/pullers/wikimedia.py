"""Wikimedia Commons candidate puller.

Fetches featured pictures via the Commons API and returns candidate entries
in sources.json shape, filtered to the open-license allowlist. Uses only the
stdlib (urllib) so the pipeline has no HTTP dependency.
"""

import json
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ALLOWED_LICENSES = {"CC0", "CC BY", "CC BY-SA", "CC BY 3.0", "CC BY-SA 3.0", "CC BY 4.0", "CC BY-SA 4.0", "Public Domain", "Public domain"}
_API = "https://commons.wikimedia.org/w/api.php"


def fetch_json(url):
    req = Request(url, headers={
        "User-Agent": "x4-wallpapers/1.0 (https://github.com/x4-wallpapers/x4-wallpapers; wallpaper store pipeline)",
    })
    with urlopen(req, timeout=60) as resp:
        return json.load(resp)


def _slugify(title):
    # "File:Aurora over Norway.jpg" -> "aurora-over-norway"
    base = title.split(":", 1)[-1]
    base = re.sub(r"\.(jpe?g|png|gif|tiff?|svg)$", "", base, flags=re.I)
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")
    return base or "wallpaper"


def _strip_artist(value):
    text = re.sub(r"\[\[(?:[^\]|]+\|)?([^\]]+)\]\]", r"\1", value)  # wikilinks
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(text.split()).strip(" .") or "Unknown"


def featured_pictures(limit=20):
    params = {
        "action": "query",
        "format": "json",
        "generator": "categorymembers",
        "gcmtitle": "Category:Featured pictures on Wikimedia Commons",
        "gcmtype": "file",
        "gcmlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
    }
    url = _API + "?" + urlencode(params)
    data = fetch_json(url)
    out = []
    for page in (data.get("query") or {}).get("pages", {}).values():
        ii = (page.get("imageinfo") or [{}])[0]
        ext = ii.get("extmetadata", {})
        license_name = (ext.get("LicenseShortName") or {}).get("value", "").strip()
        if license_name not in ALLOWED_LICENSES:
            continue
        title = (ext.get("ObjectName") or {}).get("value", "").strip() or page.get("title", "")
        author = _strip_artist((ext.get("Artist") or {}).get("value", ""))
        out.append({
            "id": _slugify(page.get("title", "")),
            "title": title,
            "author": author,
            "license": license_name,
            "attribution": f"© {author}, {license_name}",
            "category": "general",
            "source": page.get("canonicalurl") or page.get("title", ""),
            "source_url": ii.get("url", ""),
        })
    return out
