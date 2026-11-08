from pathlib import Path

import pytest

from qtag.config import default_config_dir, default_config_text, prepare_runtime, write_default_config
from qtag.tagging import DEFAULT_TRACKER_MEDIA


def test_default_config_dir_ends_with_qtag():
    assert default_config_dir().name == "qtag"


def test_default_config_contains_mam():
    text = default_config_text()
    assert "myanonamouse" in text
    assert "Ebook" in text
    assert "Audiobook" in text
    assert "Manga" in text
    assert "qbittorrent:" in text
    assert "auto_tags:" in text
    assert "tag_types:" not in text
    assert "when: [Movie, TV]" in text
    assert "overwrite:" not in text
    assert "update_tags:" not in text
    assert "max_number: -1" not in text
    assert "ignore: false" not in text
    assert "process_method" not in text
    assert "process_type" not in text
    assert "codec:" not in text
    assert "format:" in text
    assert "process:" in text
    assert "patterns:" in text
    assert "FC2:" in text


def test_write_default_config(tmp_path: Path):
    path = tmp_path / "config.yaml"
    assert write_default_config(path)
    assert path.exists()
    assert not write_default_config(path)
    assert write_default_config(path, overwrite=True)


def test_prepare_runtime_defaults():
    runtime = prepare_runtime(
        {
            "manual_tags": ["★Save"],
            "auto_tags": {
                "media": {"prefix": "#"},
                "resolution": {},
                "source": {"prefix": "$", "ignore": True},
            },
            "trackers": {
                "NHD": {"url_key": "nexushd"},
                "OpenCD": {"url_key": "open.cd", "media": ["Music"]},
                "MAM": {"url_key": "myanonamouse", "media": ["Ebook", "Audiobook", "Manga"]},
            },
        }
    )
    assert "media" in runtime["auto_tags"]
    assert "source" not in runtime["auto_tags"]
    assert runtime["auto_tags"]["media"]["max_number"] == -1
    assert runtime["auto_tags"]["media"]["when"] == []
    assert runtime["auto_tags"]["media"]["prefix"] == "#"
    assert runtime["auto_tags"]["resolution"]["prefix"] == ""
    assert runtime["trackers"]["NHD"]["media"] == list(DEFAULT_TRACKER_MEDIA)
    assert runtime["trackers"]["OpenCD"]["media"] == ["Music"]
    assert runtime["manual_tags"] == ["★Save"]
    assert "overwrite" not in runtime
    assert "update_tags" not in runtime


def test_prepare_runtime_normalizes_when():
    runtime = prepare_runtime(
        {
            "auto_tags": {
                "media": {"prefix": "#"},
                "source": {"prefix": "$", "when": "Movie"},
                "producer": {"prefix": "*", "when": ["XXX"]},
            },
        }
    )
    assert runtime["auto_tags"]["media"]["when"] == []
    assert runtime["auto_tags"]["source"]["when"] == ["Movie"]
    assert runtime["auto_tags"]["producer"]["when"] == ["XXX"]


def test_prepare_runtime_team_special():
    runtime = prepare_runtime({"auto_tags": {"team": {"prefix": "-", "special": ["D-Z0N3"]}}})
    assert runtime["auto_tags"]["team"]["special"] == ["D-Z0N3"]
    runtime = prepare_runtime({"auto_tags": {"team": {"prefix": "-"}}})
    assert runtime["auto_tags"]["team"]["special"] == []


def test_prepare_runtime_producer_patterns():
    runtime = prepare_runtime(
        {
            "auto_tags": {
                "producer": {
                    "when": ["XXX"],
                    "patterns": [{"FC2": r"fc2[ -](ppv[ -])?\d+"}, {"JAV": r"[a-zA-Z]+-\d+"}],
                }
            }
        }
    )
    patterns = runtime["auto_tags"]["producer"]["patterns"]
    assert [name for name, _ in patterns] == ["FC2", "JAV"]
    assert patterns[0][1].match("FC2-4210439")
    assert patterns[1][1].match("MIDV-518")


def test_prepare_runtime_ignores_producer():
    runtime = prepare_runtime(
        {"auto_tags": {"producer": {"ignore": True, "patterns": [{"JAV": r".+"}]}}}
    )
    assert "producer" not in runtime["auto_tags"]


def test_prepare_runtime_empty_producer_patterns():
    runtime = prepare_runtime({"auto_tags": {"producer": {"when": ["XXX"]}}})
    assert runtime["auto_tags"]["producer"]["patterns"] == []


def test_prepare_runtime_bad_producer_pattern():
    with pytest.raises(ValueError, match="invalid producer pattern"):
        prepare_runtime({"auto_tags": {"producer": {"patterns": [{"FC2": "("}]}}})
    with pytest.raises(ValueError, match="single"):
        prepare_runtime({"auto_tags": {"producer": {"patterns": ["FC2"]}}})
