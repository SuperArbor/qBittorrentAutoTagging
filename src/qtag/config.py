"""Load and bootstrap qtag configuration."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from platformdirs import user_config_dir

from qtag.tagging import DEFAULT_TRACKER_CONTENT, TAGS

APP_NAME = "qtag"
CONFIG_FILENAME = "config.yaml"


def default_config_dir() -> Path:
    """Windows Roaming / Linux ~/.config / macOS Application Support."""
    return Path(user_config_dir(appname=APP_NAME, appauthor=False, roaming=True))


def default_config_text() -> str:
    return files("qtag").joinpath("default_config.yaml").read_text(encoding="utf-8")


def write_default_config(path: Path, overwrite: bool = False) -> bool:
    if path.exists() and not overwrite:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(default_config_text(), encoding="utf-8")
    return True


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_config(config_dir: Path) -> dict[str, Any]:
    path = config_dir / CONFIG_FILENAME
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid config at {path}")
    return data


def prepare_runtime(config: dict[str, Any]) -> dict[str, Any]:
    """Normalize tag_types / trackers and collect runtime flags."""
    tag_types = {
        tag_type: dict(spec) for tag_type, spec in (config.get("tag_types") or {}).items() if not spec.get("ignore")
    }
    for spec in tag_types.values():
        spec.setdefault("prefix", "")
        if not spec.get("max_number"):
            spec["max_number"] = -1

    trackers = {name: dict(spec) for name, spec in (config.get("trackers") or {}).items()}
    for spec in trackers.values():
        if not spec.get("content"):
            spec["content"] = list(DEFAULT_TRACKER_CONTENT)
        spec.setdefault("ignore", False)
        spec.setdefault("url_key", "")

    return {
        "tag_types": tag_types,
        "trackers": trackers,
        "overwrite": bool(config.get("overwrite")),
        "tags_to_reserve": list(config.get("tags_to_reserve") or []),
        "update_tags": bool(config.get("update_tags")),
        "known_tags": TAGS,
    }
