import json
import unittest
from unittest import mock

import wikimedia

PAGE = {
    "pageid": 1,
    "title": "File:Aurora over Norway.jpg",
    "imageinfo": [{
        "url": "https://upload.wikimedia.org/wikipedia/commons/x.jpg",
        "extmetadata": {
            "ObjectName": {"value": "Aurora over Norway"},
            "Artist": {"value": "[[User:Photographer|Photo Author]]"},
            "LicenseShortName": {"value": "CC BY-SA 4.0"},
            "AttributionRequired": {"value": "true"},
            "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"},
        },
    }],
}

API_RESPONSE = {
    "query": {
        "pages": {str(PAGE["pageid"]): PAGE},
    }
}


class _FakeResp:
    def read(self):
        return b'{"ok": true}'


class _FakeCM:
    def __enter__(self):
        return _FakeResp()

    def __exit__(self, *args):
        return False


class FeaturedPicturesTest(unittest.TestCase):
    def test_fetch_json_sends_descriptive_user_agent(self):
        with mock.patch("wikimedia.urlopen", return_value=_FakeCM()) as uo:
            data = wikimedia.fetch_json("https://example.invalid/")

        uo.assert_called_once()
        req = uo.call_args.args[0]
        self.assertIn("Andrra", req.get_header("User-agent"))
        self.assertEqual(data, {"ok": True})

    def test_returns_license_filtered_candidates(self):
        with mock.patch("wikimedia.fetch_json", return_value=API_RESPONSE) as fj:
            candidates = wikimedia.featured_pictures(limit=20)

        fj.assert_called_once()
        url = fj.call_args.args[0]
        self.assertIn("generator=categorymembers", url)
        self.assertIn("gcmtitle=Category%3AFeatured", url)
        self.assertIn("gcmtype=file", url)
        self.assertIn("gcmlimit=20", url)
        self.assertEqual(len(candidates), 1)
        got = candidates[0]
        self.assertEqual(got["id"], "aurora-over-norway")
        self.assertEqual(got["title"], "Aurora over Norway")
        self.assertEqual(got["author"], "Photo Author")
        self.assertEqual(got["license"], "CC BY-SA 4.0")
        self.assertIn("Photo Author", got["attribution"])
        self.assertEqual(got["source_url"], PAGE["imageinfo"][0]["url"])
        self.assertEqual(got["source"], PAGE["title"])

    def test_skips_non_open_licenses(self):
        page = json.loads(json.dumps(PAGE))
        page["imageinfo"][0]["extmetadata"]["LicenseShortName"]["value"] = "All Rights Reserved"
        with mock.patch("wikimedia.fetch_json", return_value={"query": {"pages": {"1": page}}}):
            candidates = wikimedia.featured_pictures()
        self.assertEqual(candidates, [])


if __name__ == "__main__":
    unittest.main()
