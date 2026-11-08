import unittest

from qtag.tagging import (
    classify_content_by_files,
    decode_torrent_tags,
    prefix_tags,
    prune_statistics,
    tagging_strategy,
)


class TestDecodeTorrentTags(unittest.TestCase):
    def test_decode_torrent_tags(self):
        input_list = [
            "The.Frighteners.1996.DC.1080p.UHD.BluRay.DDP.7.1.DoVi.HDR10.x265-c0kE",
            "Mrs. Doubtfire 1993 1080p Bluray DD5.1 x264-Friday.mkv",
            "The Talented Mr. Ripley 1999 1080p BluRay DD+5.1 H265-HiDt",
            "Aruitemo Aruitemo a.k.a. Still Walking 2008 PROPER 1080p BluRay AAC2.0 H.264-LoRD",
            "Lie with Me 2005 1080i BluRay REMUX MPEG-2 DD5.1-G00DB0Y.mkv",
            "Yuru.Camp.Movie.2022.2160p.BDrip.HEVC.DV.DDP7.1.Binaural.AAC-Rainbaby",
            "FC2-PPV-4210439",
            "FC2 PPV 4210439",
            "FC2 PPV-4210439",
            "FC2 4210439",
            "FC2-4210439",
            "MIDV-518",
        ]
        expected_output_list = [
            {
                "content": "Movie",
                "name": "The Frighteners",
                "media": "BluRay",
                "year": "1996",
                "resolution": "1080p",
                "process_method": "x265",
                "process_type": "Encode",
                "team": "c0kE",
                "producer": "",
            },
            {
                "content": "Movie",
                "name": "Mrs. Doubtfire",
                "media": "BluRay",
                "year": "1993",
                "resolution": "1080p",
                "process_method": "x264",
                "process_type": "Encode",
                "team": "Friday",
                "producer": "",
            },
            {
                "content": "Movie",
                "name": "The Talented Mr. Ripley",
                "media": "BluRay",
                "year": "1999",
                "resolution": "1080p",
                "process_method": "H.265",
                "process_type": "Raw",
                "team": "HiDt",
                "producer": "",
            },
            {
                "content": "Movie",
                "name": "Aruitemo Aruitemo a.k.a. Still Walking",
                "media": "BluRay",
                "year": "2008",
                "resolution": "1080p",
                "process_method": "H.264",
                "process_type": "Raw",
                "team": "LoRD",
                "producer": "",
            },
            {
                "content": "Movie",
                "name": "Lie with Me",
                "media": "BluRay",
                "year": "2005",
                "resolution": "1080i",
                "process_method": "MPEG-2",
                "process_type": "Raw",
                "team": "G00DB0Y",
                "producer": "",
            },
            {
                "content": "Movie",
                "name": "Yuru Camp Movie",
                "media": "BluRay",
                "year": "2022",
                "resolution": "2160p",
                "process_method": "H.265",
                "process_type": "Raw",
                "team": "Rainbaby",
                "producer": "",
            },
            {"content": "XXX", "producer": "FC2"},
            {"content": "XXX", "producer": "FC2"},
            {"content": "XXX", "producer": "FC2"},
            {"content": "XXX", "producer": "FC2"},
            {"content": "XXX", "producer": "FC2"},
            {"content": "XXX", "producer": "JAV"},
        ]
        for torrent_name, expected_output in zip(input_list, expected_output_list, strict=True):
            tags = decode_torrent_tags(torrent_name, teams=[], tag_types=[], try_xxx=True)
            self.assertEqual(tags, expected_output)

    def test_irregular_team(self):
        torrent_name = "Begin Again 2014 1080p BluRay x264 EbP"
        tags = decode_torrent_tags(torrent_name)
        self.assertEqual(tags["team"], "")
        tags = decode_torrent_tags(torrent_name, teams=["EbP"])
        self.assertEqual(tags["team"], "EbP")

    def test_tag_types_subset(self):
        tag_types_all = ["content", "name", "media", "year", "resolution", "process_method", "process_type", "team"]
        combinations = [[0], [0, 1], [2, 4], [3, 4, 5], [7], list(range(len(tag_types_all)))]
        torrent_name = "The.Frighteners.1996.DC.1080p.UHD.BluRay.DDP.7.1.DoVi.HDR10.x265-c0kE"
        for comb in combinations:
            tag_types = [tag_types_all[i] for i in comb]
            tags = decode_torrent_tags(torrent_name, teams=[], tag_types=tag_types)
            self.assertEqual(set(tags.keys()), set(tag_types))


class TestTrackerStrategy(unittest.TestCase):
    def test_strategies(self):
        self.assertEqual(tagging_strategy(["Music"]), "music")
        self.assertEqual(tagging_strategy(["Ebook", "Audiobook"]), "files")
        self.assertEqual(tagging_strategy(["Movie", "TV"]), "name")
        self.assertEqual(tagging_strategy(["Movie", "TV", "Music", "XXX"]), "name")
        self.assertEqual(tagging_strategy(None), "name")
        self.assertEqual(tagging_strategy([]), "name")


class TestClassifyByFiles(unittest.TestCase):
    def test_ebook_multi_format(self):
        files = [
            "Author - Title/Title.epub",
            "Author - Title/Title.mobi",
            "Author - Title/Title.azw3",
            "Author - Title/cover.jpg",
            "Author - Title/metadata.opf",
        ]
        self.assertEqual(classify_content_by_files(files), "Ebook")

    def test_ebook_collection(self):
        files = ["Omnibus/book1.epub", "Omnibus/book2.epub", "Omnibus/book3.azw3"]
        self.assertEqual(classify_content_by_files(files), "Ebook")

    def test_audiobook_single(self):
        self.assertEqual(classify_content_by_files(["Book.m4b"]), "Audiobook")

    def test_audiobook_split_with_sidecars(self):
        files = [
            "Book/cover.jpg",
            "Book/book.cue",
            "Book/book.nfo",
            "Book/01.mp3",
            "Book/02.mp3",
            "Book/03.mp3",
        ]
        self.assertEqual(classify_content_by_files(files), "Audiobook")

    def test_both_prefers_audiobook(self):
        files = ["Title/book.epub", "Title/book.m4b", "Title/cover.png"]
        self.assertEqual(classify_content_by_files(files), "Audiobook")

    def test_nested_epub_in_zip_suffix(self):
        self.assertEqual(classify_content_by_files(["Title.epub.zip"]), "Ebook")

    def test_keyword_fallback(self):
        self.assertEqual(classify_content_by_files(["archive.zip"], "Some Book EPUB"), "Ebook")
        self.assertEqual(classify_content_by_files(["archive.rar"], "Some Book M4B"), "Audiobook")

    def test_sidecars_only(self):
        self.assertEqual(classify_content_by_files(["cover.jpg", "readme.txt", "book.cue"]), "")


class TestPrefixAndPrune(unittest.TestCase):
    def test_prefix_tags_skips_empty(self):
        tag_types = {
            "content": {"prefix": "#"},
            "team": {"prefix": "-"},
        }
        tags_ui = prefix_tags({"content": "Ebook", "team": ""}, tag_types)
        self.assertEqual(tags_ui, {"content": "#Ebook", "team": ""})

    def test_prune_statistics(self):
        statistics = {
            "TOTAL": {"content": {"Ebook": 2, "Movie": 0}, "team": {"A": 0}},
            "CATEGORIES": {
                "MAM": {"content": {"Ebook": 2, "Audiobook": 0}},
                "Empty": {"content": {"Movie": 0}},
            },
        }
        pruned = prune_statistics(statistics)
        self.assertEqual(pruned["TOTAL"], {"content": {"Ebook": 2}})
        self.assertEqual(pruned["CATEGORIES"], {"MAM": {"content": {"Ebook": 2}}})
