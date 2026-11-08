"""Pure tagging helpers: name decoding, file-type classification, prefixes."""

from __future__ import annotations

import datetime
import os
import re
from pathlib import Path

SPLITTERS = [".", " "]
SPLITTER_TEAM = "-"
VIDEO_EXTS = [".mkv", ".mp4"]
MEDIA_TYPES_MORE = ["BluRay", "Blu-ray", "BDRip", "DVD", "DVDRip", "HDDVD", "HDTV", "WEB", "WEB-DL", "WEBRip"]
YEAR_MIN = 1900
YEAR_MAX = datetime.datetime.now().astimezone().year
UNKNOWN_TAG = "?"

DEFAULT_TRACKER_CONTENT = ["Movie", "TV", "Music"]
FILE_CONTENTS = frozenset({"Ebook", "Audiobook"})
VIDEO_CONTENTS = frozenset({"Movie", "TV"})

TAGS = {
    "content": ["Movie", "TV", "Music", "XXX", "Ebook", "Audiobook"],
    "media": ["BluRay", "WEB", "DVD", "HDTV"],
    "process_type": ["Encode", "Raw"],
    "process_method": ["x264", "x265", "H.264", "H.265", "XviD", "DivX", "MPEG-2"],
    "resolution": ["1080", "2160", "720"],
}

DEFAULT_TAG_TYPES = [
    "content",
    "name",
    "media",
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


def tagging_strategy(content_types: list[str] | None) -> str:
    """Pick a tagging path from a tracker's configured content list."""
    if not content_types:
        return "name"
    types = set(content_types)
    if types == {"Music"}:
        return "music"
    if types & FILE_CONTENTS and not (types & VIDEO_CONTENTS):
        return "files"
    return "name"


def classify_content_by_files(file_names: list[str], torrent_name: str = "") -> str:
    """Classify Ebook vs Audiobook from torrent file paths.

    Sidecar files (covers, cue, nfo, ...) are ignored. Multiple ebook formats of
    the same title still count as Ebook. If both kinds of content files appear,
    Audiobook wins.
    """
    has_ebook = False
    has_audiobook = False
    for name in file_names:
        exts = {suffix.lower() for suffix in Path(name).suffixes}
        content_exts = exts - IGNORE_EXTS
        if content_exts & AUDIOBOOK_EXTS:
            has_audiobook = True
        if content_exts & EBOOK_EXTS:
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


def prefix_tags(tags: dict[str, str], tag_types: dict[str, dict]) -> dict[str, str]:
    tags_ui: dict[str, str] = {}
    for tag_type, tag_value in tags.items():
        spec = tag_types.get(tag_type)
        if spec is None:
            continue
        tags_ui[tag_type] = f"{spec['prefix']}{tag_value}" if tag_value else ""
    return tags_ui


def decode_torrent_tags_xxx(torrent_name: str, tag_types: list[str]) -> dict[str, str]:
    content = ""
    producer = ""
    if re.match(r"[a-zA-Z]+-\d+", torrent_name, re.IGNORECASE):
        content = "XXX"
        producer = "JAV"
    elif re.match(r"fc2[ -](ppv[ -])?\d+", torrent_name, re.IGNORECASE):
        content = "XXX"
        producer = "FC2"
    elif re.match(r"\d+[a-zA-Z]+-\d+", torrent_name, re.IGNORECASE):
        content = "XXX"
        producer = "SHIRO"

    decoded = {"content": content, "producer": producer}
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
        return decode_torrent_tags_xxx(torrent_name, tag_types=tag_types) if try_xxx else {"content": ""}

    groups = torrent_name.split(splitter)
    producer = ""
    media = ""
    resolution = ""
    groups_lowered = [group.lower() for group in groups]
    marked: list[int] = []

    for media_type in MEDIA_TYPES_MORE:
        for i, group in enumerate(groups_lowered):
            if media_type.lower() != group:
                continue
            if group in BLURAY_ALIASES:
                media = "BluRay"
            elif group in WEB_ALIASES:
                media = "WEB"
            elif group in DVD_ALIASES:
                media = "DVD"
            elif group in HDTV_ALIASES:
                media = "HDTV"
            else:
                media = media_type
            marked.append(i)
            break
        if media:
            break

    if not media:
        for i, group in enumerate(groups_lowered):
            if i in marked:
                continue
            if group == "uhd":
                media = "BluRay"
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

    if (not media) and (not resolution):
        return decode_torrent_tags_xxx(torrent_name, tag_types=tag_types) if try_xxx else {"content": ""}

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
    content = ""
    if "year" in tag_types or "content" in tag_types:
        for i in reversed(range(len(groups_lowered))):
            if year and content:
                break
            if i in marked:
                continue
            if re.match(r"s\d\d.*", groups_lowered[i], re.IGNORECASE):
                content = "TV"
                marked.append(i)
                continue
            try:
                if YEAR_MIN <= int(groups[i]) <= YEAR_MAX:
                    year = groups[i]
                    marked.append(i)
            except ValueError:
                pass
        if not content:
            content = "Movie"

    name = ""
    if "name" in tag_types and marked:
        marked.sort()
        name_idx = marked[0]
        name = " ".join(groups[i] for i in range(name_idx))

    decoded = {
        "content": content,
        "name": name,
        "media": media,
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
