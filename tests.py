import unittest, os
from qbittorrent_auto_tagging import decode_torrent_tags, handle_torrent_tags, process_new, process_all

current_dir = os.path.dirname(__file__)
path_config = os.path.join(current_dir, 'config.yaml')
path_statistics = os.path.join(current_dir, 'statistics.yaml')

class TestAutoTaggingMethods(unittest.TestCase):
    def test_decode_torrent_tags(self):
        # full tests
        input_list = [
            'The.Frighteners.1996.DC.1080p.UHD.BluRay.DDP.7.1.DoVi.HDR10.x265-c0kE',
            'Mrs. Doubtfire 1993 1080p Bluray DD5.1 x264-Friday.mkv',
            'The Talented Mr. Ripley 1999 1080p BluRay DD+5.1 x264-HiDt',
            'Aruitemo Aruitemo a.k.a. Still Walking 2008 PROPER 1080p BluRay AAC2.0 x264-LoRD',
            'Lie with Me 2005 1080i BluRay REMUX MPEG-2 DD5.1-G00DB0Y.mkv',
            'Yuru.Camp.Movie.2022.2160p.BDrip.HEVC.DV.DDP7.1.Binaural.AAC-Rainbaby'
        ]
        expected_output_list = [
            {'content': 'Movie', 'name': 'The Frighteners', 'media': 'BluRay', 'year': '1996', 'resolution': '1080p', 'process_method': 'x265', 'process_type': 'Encode', 'team': 'c0kE'},
            {'content': 'Movie', 'name': 'Mrs. Doubtfire', 'media': 'BluRay', 'year': '1993', 'resolution': '1080p', 'process_method': 'x264', 'process_type': 'Encode', 'team': 'Friday'},
            {'content': 'Movie', 'name': 'The Talented Mr. Ripley', 'media': 'BluRay', 'year': '1999', 'resolution': '1080p', 'process_method': 'x264', 'process_type': 'Encode', 'team': 'HiDt'},
            {'content': 'Movie', 'name': 'Aruitemo Aruitemo a.k.a. Still Walking', 'media': 'BluRay', 'year': '2008', 'resolution': '1080p', 'process_method': 'x264', 'process_type': 'Encode', 'team': 'LoRD'},
            {'content': 'Movie', 'name': 'Lie with Me', 'media': 'BluRay', 'year': '2005', 'resolution': '1080i', 'process_method': 'MPEG-2', 'process_type': 'Raw', 'team': 'G00DB0Y'},
            {'content': 'Movie', 'name': 'Yuru Camp Movie', 'media': 'BluRay', 'year': '2022', 'resolution': '2160p', 'process_method': 'H.265', 'process_type': 'Raw', 'team': 'Rainbaby'}
        ]
        for i in range(len(input_list)):
            torrent_name = input_list[i]
            expected_output = expected_output_list[i]
            tags = decode_torrent_tags(torrent_name)
            print(tags)
            self.assertEquals(tags, expected_output)
        
        # test irregular team
        torrent_name = 'Begin Again 2014 1080p BluRay x264 EbP'
        tags = decode_torrent_tags(torrent_name)
        self.assertEquals(tags['team'], '')
        tags = decode_torrent_tags(torrent_name, teams=['EbP'])
        self.assertEquals(tags['team'], 'EbP')
        
        # test with tag_types specified
        tag_types_all = ['content', 'name', 'media', 'year', 'resolution', 'process_method', 'process_type', 'team']
        combinations = [[0], [0, 1], [2, 4], [3, 4, 5], [7], list(range(len(tag_types_all)))]
        torrent_name = 'The.Frighteners.1996.DC.1080p.UHD.BluRay.DDP.7.1.DoVi.HDR10.x265-c0kE'
        for comb in combinations:
            tag_types = [tag_types_all[i] for i in comb]
            tags = decode_torrent_tags(torrent_name, teams=[], tag_types=tag_types)
            self.assertEquals(set(tags.keys()), set(tag_types))
        