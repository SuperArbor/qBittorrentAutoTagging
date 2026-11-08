from pathlib import Path

from qtag.config import default_config_dir, default_config_text, prepare_runtime, write_default_config
from qtag.tagging import DEFAULT_TRACKER_CONTENT


def test_default_config_dir_ends_with_qtag():
    assert default_config_dir().name == "qtag"


def test_default_config_contains_mam():
    text = default_config_text()
    assert "myanonamouse" in text
    assert "Ebook" in text
    assert "Audiobook" in text


def test_write_default_config(tmp_path: Path):
    path = tmp_path / "config.yaml"
    assert write_default_config(path)
    assert path.exists()
    assert not write_default_config(path)
    assert write_default_config(path, overwrite=True)


def test_prepare_runtime_defaults():
    runtime = prepare_runtime(
        {
            "overwrite": True,
            "update_tags": False,
            "tags_to_reserve": ["★Save"],
            "tag_types": {
                "content": {"prefix": "#", "ignore": False},
                "media": {"prefix": "$", "ignore": True},
            },
            "trackers": {
                "NHD": {"url_key": "nexushd"},
                "OpenCD": {"url_key": "open.cd", "content": ["Music"]},
                "MAM": {"url_key": "myanonamouse", "content": ["Ebook", "Audiobook"]},
            },
        }
    )
    assert "content" in runtime["tag_types"]
    assert "media" not in runtime["tag_types"]
    assert runtime["tag_types"]["content"]["max_number"] == -1
    assert runtime["trackers"]["NHD"]["content"] == list(DEFAULT_TRACKER_CONTENT)
    assert runtime["trackers"]["OpenCD"]["content"] == ["Music"]
    assert runtime["overwrite"] is True
    assert runtime["update_tags"] is False
