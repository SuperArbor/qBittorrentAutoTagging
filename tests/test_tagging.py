import unittest

from qtag.tagging import (
    classify_media_by_files,
    decode_torrent_tags,
    filter_by_when,
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
                "media": "Movie",
                "name": "The Frighteners",
                "source": "BluRay",
                "year": "1996",
                "resolution": "1080p",
                "process_method": "x265",
                "process_type": "Encode",
                "team": "c0kE",
                "producer": "",
            },
            {
                "media": "Movie",
                "name": "Mrs. Doubtfire",
                "source": "BluRay",
                "year": "1993",
                "resolution": "1080p",
                "process_method": "x264",
                "process_type": "Encode",
                "team": "Friday",
                "producer": "",
            },
            {
                "media": "Movie",
                "name": "The Talented Mr. Ripley",
                "source": "BluRay",
                "year": "1999",
                "resolution": "1080p",
                "process_method": "H.265",
                "process_type": "Raw",
                "team": "HiDt",
                "producer": "",
            },
            {
                "media": "Movie",
                "name": "Aruitemo Aruitemo a.k.a. Still Walking",
                "source": "BluRay",
                "year": "2008",
                "resolution": "1080p",
                "process_method": "H.264",
                "process_type": "Raw",
                "team": "LoRD",
                "producer": "",
            },
            {
                "media": "Movie",
                "name": "Lie with Me",
                "source": "BluRay",
                "year": "2005",
                "resolution": "1080i",
                "process_method": "MPEG-2",
                "process_type": "Raw",
                "team": "G00DB0Y",
                "producer": "",
            },
            {
                "media": "Movie",
                "name": "Yuru Camp Movie",
                "source": "BluRay",
                "year": "2022",
                "resolution": "2160p",
                "process_method": "H.265",
                "process_type": "Raw",
                "team": "Rainbaby",
                "producer": "",
            },
            {"media": "XXX", "producer": "FC2"},
            {"media": "XXX", "producer": "FC2"},
            {"media": "XXX", "producer": "FC2"},
            {"media": "XXX", "producer": "FC2"},
            {"media": "XXX", "producer": "FC2"},
            {"media": "XXX", "producer": "JAV"},
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
        tag_types_all = ["media", "name", "source", "year", "resolution", "process_method", "process_type", "team"]
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
        self.assertEqual(classify_media_by_files(files), "Ebook")

    def test_ebook_collection(self):
        files = ["Omnibus/book1.epub", "Omnibus/book2.epub", "Omnibus/book3.azw3"]
        self.assertEqual(classify_media_by_files(files), "Ebook")

    def test_audiobook_single(self):
        self.assertEqual(classify_media_by_files(["Book.m4b"]), "Audiobook")

    def test_audiobook_split_with_sidecars(self):
        files = [
            "Book/cover.jpg",
            "Book/book.cue",
            "Book/book.nfo",
            "Book/01.mp3",
            "Book/02.mp3",
            "Book/03.mp3",
        ]
        self.assertEqual(classify_media_by_files(files), "Audiobook")

    def test_both_prefers_audiobook(self):
        files = ["Title/book.epub", "Title/book.m4b", "Title/cover.png"]
        self.assertEqual(classify_media_by_files(files), "Audiobook")

    def test_nested_epub_in_zip_suffix(self):
        self.assertEqual(classify_media_by_files(["Title.epub.zip"]), "Ebook")

    def test_keyword_fallback(self):
        self.assertEqual(classify_media_by_files(["archive.zip"], "Some Book EPUB"), "Ebook")
        self.assertEqual(classify_media_by_files(["archive.rar"], "Some Book M4B"), "Audiobook")

    def test_sidecars_only(self):
        self.assertEqual(classify_media_by_files(["cover.jpg", "readme.txt", "book.cue"]), "")


class TestFilterByWhen(unittest.TestCase):
    def test_keeps_unconstrained_and_matching(self):
        auto_tags = {
            "media": {"prefix": "#", "when": []},
            "source": {"prefix": "$", "when": ["Movie", "TV"]},
            "producer": {"prefix": "*", "when": ["XXX"]},
        }
        tags = {"media": "Movie", "source": "BluRay", "producer": "JAV"}
        self.assertEqual(
            filter_by_when(tags, auto_tags),
            {"media": "Movie", "source": "BluRay"},
        )

    def test_drops_when_media_does_not_match(self):
        auto_tags = {
            "media": {"prefix": "#", "when": []},
            "source": {"prefix": "$", "when": ["Movie", "TV"]},
            "resolution": {"prefix": "", "when": ["Movie", "TV"]},
        }
        tags = {"media": "Ebook", "source": "BluRay", "resolution": "1080p"}
        self.assertEqual(filter_by_when(tags, auto_tags), {"media": "Ebook"})

    def test_empty_media_fails_when(self):
        auto_tags = {
            "media": {"when": []},
            "source": {"when": ["Movie", "TV"]},
        }
        tags = {"media": "", "source": "WEB"}
        self.assertEqual(filter_by_when(tags, auto_tags), {"media": ""})


class TestPrefixAndPrune(unittest.TestCase):
    def test_prefix_tags_skips_empty(self):
        auto_tags = {
            "media": {"prefix": "#"},
            "team": {"prefix": "-"},
            "resolution": {},
        }
        tags_ui = prefix_tags({"media": "Ebook", "team": "", "resolution": "1080p"}, auto_tags)
        self.assertEqual(tags_ui, {"media": "#Ebook", "team": "", "resolution": "1080p"})

    def test_prune_statistics(self):
        statistics = {
            "TOTAL": {"media": {"Ebook": 2, "Movie": 0}, "team": {"A": 0}},
            "CATEGORIES": {
                "MAM": {"media": {"Ebook": 2, "Audiobook": 0}},
                "Empty": {"media": {"Movie": 0}},
            },
        }
        pruned = prune_statistics(statistics)
        self.assertEqual(pruned["TOTAL"], {"media": {"Ebook": 2}})
        self.assertEqual(pruned["CATEGORIES"], {"MAM": {"media": {"Ebook": 2}}})
