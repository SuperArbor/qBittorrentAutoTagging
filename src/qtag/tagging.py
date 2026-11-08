"""Pure tagging helpers: name decoding, file-type classification, prefixes."""

from __future__ import annotations

import datetime
import os
import re
from pathlib import Path

SPLITTERS = [".", " "]
SPLITTER_TEAM = "-"
VIDEO_EXTS = [".mkv", ".mp4"]
SOURCE_TYPES_MORE = ["BluRay", "Blu-ray", "BDRip", "DVD", "DVDRip", "HDDVD", "HDTV", "WEB", "WEB-DL", "WEBRip"]
YEAR_MIN = 1900
YEAR_MAX = datetime.datetime.now().astimezone().year
UNKNOWN_TAG = "?"

DEFAULT_TRACKER_MEDIA = ["Movie", "TV", "Music"]
FILE_MEDIA = frozenset({"Ebook", "Audiobook"})
VIDEO_MEDIA = frozenset({"Movie", "TV"})

TAGS = {
    "media": ["Movie", "TV", "Music", "XXX", "Ebook", "Audiobook"],
    "source": ["BluRay", "WEB", "DVD", "HDTV"],
    "process_type": ["Encode", "Raw"],
    "process_method": ["x264", "x265", "H.264", "H.265", "XviD", "DivX", "MPEG-2"],
    "resolution": ["1080", "2160", "720"],
}

DEFAULT_TAG_TYPES = [
    "media",
    "name",
    "source",
    "year",
    "resolution",
    "process_method",
    "process_type",
    "team",
    "producer",
]

EBOOK_EXTS = frozenset(
    {
        ".epub",
        ".mobi",
        ".azw",
        ".azw3",
        ".azw4",
        ".kfx",
        ".fb2",
        ".pdf",
        ".djvu",
        ".lit",
    }
)
AUDIOBOOK_EXTS = frozenset(
    {
        ".m4b",
        ".mp3",
        ".m4a",
        ".flac",
        ".ogg",
        ".opus",
        ".aac",
        ".wma",
        ".wav",
    }
)
IGNORE_EXTS = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".webp",
        ".tif",
        ".tiff",
        ".cue",
        ".nfo",
        ".txt",
        ".log",
        ".sfv",
        ".md5",
        ".m3u",
        ".m3u8",
        ".pls",
        ".url",
        ".ini",
        ".xml",
        ".html",
        ".htm",
        ".css",
        ".srt",
        ".ass",
        ".ssa",
        ".vtt",
        ".opf",
        ".ncx",
    }
)
EBOOK_KEYWORDS = ("epub", "mobi", "azw3", "azw", "kfx", "fb2")
AUDIOBOOK_KEYWORDS = ("m4b", "audiobook", "unabridged")

BLURAY_ALIASES = {"bluray", "blu-ray", "bdrip"}
WEB_ALIASES = {"web", "web-dl", "webrip"}
DVD_ALIASES = {"dvd", "hddvd", "dvdrip"}
HDTV_ALIASES = {"hdtv"}


def tagging_strategy(media_types: list[str] | None) -> str:
    """Pick a tagging path from a tracker's configured media list."""
    if not media_types:
        return "name"
    types = set(media_types)
    if types == {"Music"}:
        return "music"
    if types & FILE_MEDIA and not (types & VIDEO_MEDIA):
        return "files"
    return "name"


def classify_media_by_files(file_names: list[str], torrent_name: str = "") -> str:
    """Classify Ebook vs Audiobook from torrent file paths.

    Sidecar files (covers, cue, nfo, ...) are ignored. Multiple ebook formats of
    the same title still count as Ebook. If both kinds of media files appear,
    Audiobook wins.
    """
    has_ebook = False
    has_audiobook = False
    for name in file_names:
        exts = {suffix.lower() for suffix in Path(name).suffixes}
        media_exts = exts - IGNORE_EXTS
        if media_exts & AUDIOBOOK_EXTS:
            has_audiobook = True
        if media_exts & EBOOK_EXTS:
            has_ebook = True

    if not has_ebook and not has_audiobook:
        blob = " ".join([torrent_name, *file_names]).lower()
        if any(keyword in blob for keyword in AUDIOBOOK_KEYWORDS):
            has_audiobook = True
        if any(keyword in blob for keyword in EBOOK_KEYWORDS):
            has_ebook = True

    if has_audiobook:
        return "Audiobook"
    if has_ebook:
        return "Ebook"
    return ""


def filter_by_when(tags: dict[str, str], auto_tags: dict[str, dict]) -> dict[str, str]:
    """Keep an auto tag only if it has no `when`, or media is in `when`."""
    media = tags.get("media") or ""
    filtered: dict[str, str] = {}
    for name, value in tags.items():
        allowed = (auto_tags.get(name) or {}).get("when") or []
        if allowed and media not in allowed:
            continue
        filtered[name] = value
    return filtered


def prefix_tags(tags: dict[str, str], auto_tags: dict[str, dict]) -> dict[str, str]:
    tags_ui: dict[str, str] = {}
    for name, tag_value in tags.items():
        spec = auto_tags.get(name)
        if spec is None:
            continue
        prefix = spec.get("prefix") or ""
        tags_ui[name] = f"{prefix}{tag_value}" if tag_value else ""
    return tags_ui


def decode_torrent_tags_xxx(torrent_name: str, tag_types: list[str]) -> dict[str, str]:
    media = ""
    producer = ""
    if re.match(r"[a-zA-Z]+-\d+", torrent_name, re.IGNORECASE):
        media = "XXX"
        producer = "JAV"
    elif re.match(r"fc2[ -](ppv[ -])?\d+", torrent_name, re.IGNORECASE):
        media = "XXX"
        producer = "FC2"
    elif re.match(r"\d+[a-zA-Z]+-\d+", torrent_name, re.IGNORECASE):
        media = "XXX"
        producer = "SHIRO"

    decoded = {"media": media, "producer": producer}
    return {tag_type: decoded[tag_type] for tag_type in tag_types if tag_type in decoded}


def decode_torrent_tags(
    torrent_name: str,
    teams: list[str] | None = None,
    tag_types: list[str] | None = None,
    try_xxx: bool = False,
) -> dict[str, str]:
    """Decode a Movie/TV torrent name into tags."""
    teams = teams or []
    if not tag_types:
        tag_types = list(DEFAULT_TAG_TYPES)

    root, ext = os.path.splitext(torrent_name)
    if ext.lower() in VIDEO_EXTS:
        torrent_name = root

    splitter = ""
    current_best = 0
    min_groups = 3
    for candidate in SPLITTERS:
        groups_test = torrent_name.split(candidate)
        if len(groups_test) >= max(min_groups, current_best):
            current_best = len(groups_test)
            splitter = candidate

    if not splitter:
        return decode_torrent_tags_xxx(torrent_name, tag_types=tag_types) if try_xxx else {"media": ""}

    groups = torrent_name.split(splitter)
    producer = ""
    source = ""
    resolution = ""
    groups_lowered = [group.lower() for group in groups]
    marked: list[int] = []

    for source_type in SOURCE_TYPES_MORE:
        for i, group in enumerate(groups_lowered):
            if source_type.lower() != group:
                continue
            if group in BLURAY_ALIASES:
                source = "BluRay"
            elif group in WEB_ALIASES:
                source = "WEB"
            elif group in DVD_ALIASES:
                source = "DVD"
            elif group in HDTV_ALIASES:
                source = "HDTV"
            else:
                source = source_type
            marked.append(i)
            break
        if source:
            break

    if not source:
        for i, group in enumerate(groups_lowered):
            if i in marked:
                continue
            if group == "uhd":
                source = "BluRay"
                marked.append(i)
                break

    for reso_type in TAGS["resolution"]:
        for i, group in enumerate(groups_lowered):
            if i in marked:
                continue
            if re.match(reso_type + r"[pi]", group):
                resolution = group
                marked.append(i)
                break
        if resolution:
            break

    if (not source) and (not resolution):
        return decode_torrent_tags_xxx(torrent_name, tag_types=tag_types) if try_xxx else {"media": ""}

    team = ""
    if "team" in tag_types:
        last_item = groups.pop()
        last_items = last_item.split(SPLITTER_TEAM)
        groups.extend(last_items)
        groups_lowered = [group.lower() for group in groups]
        if len(last_items) == 2:
            team = last_items[1]
            marked.append(len(groups) - 1)
        elif len(last_items) == 1 and last_item in teams:
            team = last_item
            marked.append(len(groups) - 1)

    process_method = ""
    process_type = ""
    if "process_method" in tag_types or "process_type" in tag_types:
        codec = re.compile(
            r"(x26\d)|(h26\d)|(h\.?26\d)|(avc)|(hevc)|(xvid)|(divx)|(mpeg-2)",
            re.IGNORECASE,
        )
        for i, group in enumerate(groups_lowered):
            if i in marked:
                continue
            match = codec.match(group)
            if not match:
                continue
            if match.group(1):
                process_method = match.group(1)
                process_type = "Encode"
            elif match.group(2):
                process_method = f"H.{match.group(2)[1:]}"
                process_type = "Raw"
            elif match.group(3):
                process_method = str.upper(match.group(3))
                process_type = "Raw"
            elif match.group(4):
                process_method = "H.264"
                process_type = "Raw"
            elif match.group(5):
                process_method = "H.265"
                process_type = "Raw"
            elif match.group(6):
                process_method = "XviD"
                process_type = "Encode"
            elif match.group(7):
                process_method = "DivX"
                process_type = "Encode"
            elif match.group(8):
                process_method = "MPEG-2"
                process_type = "Raw"
            marked.append(i)
            break

    year = ""
    media = ""
    if "year" in tag_types or "media" in tag_types:
        for i in reversed(range(len(groups_lowered))):
            if year and media:
                break
            if i in marked:
                continue
            if re.match(r"s\d\d.*", groups_lowered[i], re.IGNORECASE):
                media = "TV"
                marked.append(i)
                continue
            try:
                if YEAR_MIN <= int(groups[i]) <= YEAR_MAX:
                    year = groups[i]
                    marked.append(i)
            except ValueError:
                pass
        if not media:
            media = "Movie"

    name = ""
    if "name" in tag_types and marked:
        marked.sort()
        name_idx = marked[0]
        name = " ".join(groups[i] for i in range(name_idx))

    decoded = {
        "media": media,
        "name": name,
        "source": source,
        "year": year,
        "resolution": resolution,
        "process_method": process_method,
        "process_type": process_type,
        "team": team,
        "producer": producer,
    }
    return {tag_type: decoded.get(tag_type, "") for tag_type in tag_types}


def prune_statistics(statistics: dict) -> dict:
    result: dict = {"TOTAL": {}, "CATEGORIES": {}}
    for tag_type, counts in (statistics.get("TOTAL") or {}).items():
        kept = {tag: number for tag, number in counts.items() if number > 0}
        if kept:
            result["TOTAL"][tag_type] = kept
    for category, types in (statistics.get("CATEGORIES") or {}).items():
        kept_types = {}
        for tag_type, counts in types.items():
            kept = {tag: number for tag, number in counts.items() if number > 0}
            if kept:
                kept_types[tag_type] = kept
        if kept_types:
            result["CATEGORIES"][category] = kept_types
    return result
