"""Load and bootstrap qtag configuration."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from platformdirs import user_config_dir

from qtag.tagging import DEFAULT_TRACKER_MEDIA, TAGS, compile_producer_patterns

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
    """Normalize auto_tags / trackers and collect runtime flags."""
    auto_tags = {
        name: dict(spec) for name, spec in (config.get("auto_tags") or {}).items() if not spec.get("ignore")
    }
    for name, spec in auto_tags.items():
        if spec.get("prefix") is None:
            spec["prefix"] = ""
        if spec.get("max_number") in (None, 0):
            spec["max_number"] = -1
        when = spec.get("when") or []
        spec["when"] = [when] if isinstance(when, str) else list(when)
        if name == "team":
            special = spec.get("special") or []
            spec["special"] = [special] if isinstance(special, str) else [str(item) for item in special]
        if name == "producer":
            spec["patterns"] = compile_producer_patterns(spec.get("patterns"))

    trackers = {name: dict(spec) for name, spec in (config.get("trackers") or {}).items()}
    for spec in trackers.values():
        if not spec.get("media"):
            spec["media"] = list(DEFAULT_TRACKER_MEDIA)
        spec.setdefault("ignore", False)
        spec.setdefault("url_key", "")

    return {
        "auto_tags": auto_tags,
        "trackers": trackers,
        "manual_tags": list(config.get("manual_tags") or []),
        "known_tags": TAGS,
    }
