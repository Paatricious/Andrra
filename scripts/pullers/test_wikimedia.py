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

    def test_skips_non_image_files(self):
        page = json.loads(json.dumps(PAGE))
        page["title"] = "File:Some Video.webm"
        page["imageinfo"][0]["url"] = "https://upload.wikimedia.org/wikipedia/commons/v.webm"
        with mock.patch("wikimedia.fetch_json", return_value={"query": {"pages": {"1": page}}}):
            candidates = wikimedia.featured_pictures()
        self.assertEqual(candidates, [])

    def test_title_with_multilingual_label_dump_is_cleaned(self):
        page = json.loads(json.dumps(PAGE))
        page["imageinfo"][0]["extmetadata"]["ObjectName"]["value"] = (
            'Italian: Scuola di Atene The School of Athenstitle QS:P1476,it:"Scuola di Atene "'
            'label QS:Lit,"Scuola di Atene "label QS:Les,"La escuela de Atenas"label QS:Len,"The School of Athens"'
        )
        with mock.patch("wikimedia.fetch_json", return_value={"query": {"pages": {"1": page}}}):
            candidates = wikimedia.featured_pictures()
        self.assertEqual(candidates[0]["title"], "Italian: Scuola di Atene The School of Athens")

    def test_title_with_wind_mountain_label_blob_is_cleaned(self):
        page = json.loads(json.dumps(PAGE))
        page["imageinfo"][0]["extmetadata"]["ObjectName"]["value"] = 'Wind Mountainlabel QS:Len,"Wind Mountain"'
        with mock.patch("wikimedia.fetch_json", return_value={"query": {"pages": {"1": page}}}):
            candidates = wikimedia.featured_pictures()
        self.assertEqual(candidates[0]["title"], "Wind Mountain")

    def test_title_with_filename_numbering_is_cleaned(self):
        page = json.loads(json.dumps(PAGE))
        page["imageinfo"][0]["extmetadata"]["ObjectName"]["value"] = "001 Chateau de Chillon and Dents du Midi Photo by Giles Laurent"
        with mock.patch("wikimedia.fetch_json", return_value={"query": {"pages": {"1": page}}}):
            candidates = wikimedia.featured_pictures()
        self.assertEqual(candidates[0]["title"], "Chateau de Chillon and Dents du Midi Photo by Giles Laurent")

    def test_artist_html_entities_are_decoded(self):
        page = json.loads(json.dumps(PAGE))
        page["imageinfo"][0]["extmetadata"]["Artist"]["value"] = (
            "<a href='//commons.wikimedia.org/wiki/User:X'>Day &amp; Son</a>"
        )
        with mock.patch("wikimedia.fetch_json", return_value={"query": {"pages": {"1": page}}}):
            candidates = wikimedia.featured_pictures()
        self.assertEqual(candidates[0]["author"], "Day & Son")


if __name__ == "__main__":
    unittest.main()
