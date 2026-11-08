"""Pure tagging helpers: name decoding, file-type classification, prefixes."""

from __future__ import annotations

import datetime
import re
from pathlib import Path

SPLITTERS = [".", " "]
SPLITTER_TEAM = "-"
YEAR_MIN = 1900
YEAR_MAX = datetime.datetime.now().astimezone().year
UNKNOWN_TAG = "?"

DEFAULT_TRACKER_MEDIA = ["Movie", "TV", "Music"]
FILE_MEDIA = frozenset({"Ebook", "Audiobook", "Manga"})
VIDEO_MEDIA = frozenset({"Movie", "TV"})

TAGS = {
    "media": ["Movie", "TV", "Music", "XXX", "Ebook", "Audiobook", "Manga"],
    "source": ["BluRay", "WEB-DL", "WEBRip", "DVD", "HDTV", "HDDVD", "HDRip"],
    "process": ["Encode", "Raw", "Remux"],
    "format": [
        "x264",
        "x265",
        "x266",
        "H.264",
        "H.265",
        "XviD",
        "DivX",
        "MPEG-2",
        "VC-1",
        "AV1",
        "FLAC",
        "MP3",
        "M4B",
        "M4A",
        "OGG",
        "Opus",
        "AAC",
        "WMA",
        "WAV",
        "EPUB",
        "MOBI",
        "AZW",
        "AZW3",
        "AZW4",
        "KFX",
        "FB2",
        "PDF",
        "DjVu",
        "LIT",
        "CBR",
        "CBZ",
    ],
    "resolution": ["2160p", "1080p", "1080i", "720p", "720i", "480p", "mHD"],
}

DEFAULT_TAG_TYPES = [
    "media",
    "name",
    "source",
    "year",
    "resolution",
    "format",
    "process",
    "team",
    "producer",
]

# Longer tokens first so WEB-DL wins over WEB.
SOURCE_TOKEN_MAP = {
    "web-dl": "WEB-DL",
    "webdl": "WEB-DL",
    "webrip": "WEBRip",
    "web-rip": "WEBRip",
    "web": "WEB-DL",
    "bluray": "BluRay",
    "blu-ray": "BluRay",
    "bdrip": "BluRay",
    "uhd": "BluRay",
    "hdtvrip": "HDTV",
    "hdtv": "HDTV",
    "hdrip": "HDRip",
    "hddvd": "HDDVD",
    "dvdrip": "DVD",
    "dvd": "DVD",
}
RAW_PROCESS_TOKENS = frozenset({"web-dl", "webdl", "iso", "bdiso", "dvdiso"})
RESOLUTION_BASES = ("2160", "1080", "720", "480")

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
MANGA_EXTS = frozenset({".cbr", ".cbz"})
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
MANGA_KEYWORDS = ("cbr", "cbz", "manga")

FORMAT_BY_EXT = {
    ".m4b": "M4B",
    ".mp3": "MP3",
    ".m4a": "M4A",
    ".flac": "FLAC",
    ".ogg": "OGG",
    ".opus": "Opus",
    ".aac": "AAC",
    ".wma": "WMA",
    ".wav": "WAV",
    ".epub": "EPUB",
    ".mobi": "MOBI",
    ".azw": "AZW",
    ".azw3": "AZW3",
    ".azw4": "AZW4",
    ".kfx": "KFX",
    ".fb2": "FB2",
    ".pdf": "PDF",
    ".djvu": "DjVu",
    ".lit": "LIT",
    ".cbr": "CBR",
    ".cbz": "CBZ",
}

FORMAT_PATTERNS = (
    (re.compile(r"^x266$", re.I), "x266"),
    (re.compile(r"^x265$", re.I), "x265"),
    (re.compile(r"^x264$", re.I), "x264"),
    (re.compile(r"^(h\.?265|hevc)$", re.I), "H.265"),
    (re.compile(r"^(h\.?264|avc)$", re.I), "H.264"),
    (re.compile(r"^vc-?1$", re.I), "VC-1"),
    (re.compile(r"^av1$", re.I), "AV1"),
    (re.compile(r"^mpeg-?2$", re.I), "MPEG-2"),
    (re.compile(r"^xvid$", re.I), "XviD"),
    (re.compile(r"^divx$", re.I), "DivX"),
)


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
    """Classify Ebook / Audiobook / Manga from torrent file paths.

    Sidecar files (covers, cue, nfo, ...) are ignored. Multiple ebook formats of
    the same title still count as Ebook. If more than one kind appears,
    Audiobook wins, then Manga, then Ebook.
    """
    has_ebook = False
    has_audiobook = False
    has_manga = False
    for name in file_names:
        exts = {suffix.lower() for suffix in Path(name).suffixes}
        media_exts = exts - IGNORE_EXTS
        if media_exts & AUDIOBOOK_EXTS:
            has_audiobook = True
        if media_exts & MANGA_EXTS:
            has_manga = True
        if media_exts & EBOOK_EXTS:
            has_ebook = True

    if not has_ebook and not has_audiobook and not has_manga:
        blob = " ".join([torrent_name, *file_names]).lower()
        if any(keyword in blob for keyword in AUDIOBOOK_KEYWORDS):
            has_audiobook = True
        if any(keyword in blob for keyword in MANGA_KEYWORDS):
            has_manga = True
        if any(keyword in blob for keyword in EBOOK_KEYWORDS):
            has_ebook = True

    if has_audiobook:
        return "Audiobook"
    if has_manga:
        return "Manga"
    if has_ebook:
        return "Ebook"
    return ""


def classify_format_by_files(file_names: list[str]) -> str:
    """Pick the most common content format from file suffixes."""
    counts: dict[str, int] = {}
    for name in file_names:
        media_exts = {suffix.lower() for suffix in Path(name).suffixes} - IGNORE_EXTS
        for ext in media_exts:
            fmt = FORMAT_BY_EXT.get(ext)
            if fmt:
                counts[fmt] = counts.get(fmt, 0) + 1
    if not counts:
        return ""
    return max(counts, key=counts.get)


def normalize_torrent_name(torrent_name: str) -> str:
    """Normalize scene-style names before splitting into tokens."""
    name = torrent_name.strip()
    name = re.sub(r"^(\[.*?\]\s*)+", "", name)
    name = re.sub(r"((\s*\(\d+\)\s*)?\.(mkv|mp4|avi|ts|wmv|mpg|torrent))+$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\bh\.(26[456])\b", r"H/\1", name, flags=re.IGNORECASE)
    name = re.sub(r"(\b[a-zA-Z]*\d{1,2})\.(\d{1,2}\b)", r"\1/\2", name)
    name = re.sub(r"\((\d{4})\)", r"\1", name)
    name = re.sub(r"\bWEB(?!-DL)\b", "WEB-DL", name, flags=re.IGNORECASE)
    name = re.sub(r"\bweb-?rip\b", "WEBRip", name, flags=re.IGNORECASE)
    name = re.sub(r"\bblu-?ray\b", "BluRay", name, flags=re.IGNORECASE)
    name = re.sub(r"\bdvd(rip)?\b", lambda match: "DVDRip" if match.group(1) else "DVD", name, flags=re.IGNORECASE)
    name = re.sub(r"\b((?:480|720|1080|2160)[PI])\b", lambda match: match.group(1).lower(), name)
    name = re.sub(r"\bx\.?(26[456])\b", r"x\1", name, flags=re.IGNORECASE)
    if name.count(".") >= name.count(" "):
        name = re.sub(r"\.(?! )", " ", name)
    return re.sub(r" +", " ", name.replace("/", ".")).strip()


def find_special_team(text: str, special_teams: list[str]) -> str:
    if not text or not special_teams:
        return ""
    lowered = text.lower()
    for team in sorted(special_teams, key=len, reverse=True):
        needle = team.lower()
        if not needle:
            continue
        if lowered == needle:
            return team
        if lowered.endswith(needle) and lowered[-len(needle) - 1] in "-. [":
            return team
    return ""


def _match_source_token(token: str) -> str:
    return SOURCE_TOKEN_MAP.get(token.lower(), "")


def _match_format_token(token: str) -> str:
    for pattern, fmt in FORMAT_PATTERNS:
        if pattern.match(token):
            return fmt
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


def compile_producer_patterns(patterns: list | None) -> list[tuple[str, re.Pattern[str]]]:
    """Compile `producer.patterns`: a list of single-key `{name: regex}` mappings."""
    compiled: list[tuple[str, re.Pattern[str]]] = []
    for item in patterns or []:
        if not isinstance(item, dict) or len(item) != 1:
            raise ValueError("producer.patterns items must be a single {name: regex} mapping")
        name, pattern = next(iter(item.items()))
        if not isinstance(pattern, str):
            raise ValueError(f"producer pattern for {name} must be a regex string")
        try:
            compiled.append((str(name), re.compile(pattern, re.IGNORECASE)))
        except re.error as exc:
            raise ValueError(f"invalid producer pattern for {name}: {exc}") from exc
    return compiled


def decode_torrent_tags_xxx(
    torrent_name: str,
    tag_types: list[str],
    producer_patterns: list[tuple[str, re.Pattern[str]]],
) -> dict[str, str]:
    media = ""
    producer = ""
    for name, pattern in producer_patterns:
        if pattern.match(torrent_name):
            media = "XXX"
            producer = name
            break

    decoded = {"media": media, "producer": producer}
    return {tag_type: decoded[tag_type] for tag_type in tag_types if tag_type in decoded}


def decode_torrent_tags(
    torrent_name: str,
    teams: list[str] | None = None,
    tag_types: list[str] | None = None,
    try_xxx: bool = False,
    special_teams: list[str] | None = None,
    producer_patterns: list[tuple[str, re.Pattern[str]]] | None = None,
) -> dict[str, str]:
    """Decode a Movie/TV torrent name into tags."""
    teams = teams or []
    special_teams = special_teams or []
    producer_patterns = producer_patterns or []
    if not tag_types:
        tag_types = list(DEFAULT_TAG_TYPES)

    torrent_name = normalize_torrent_name(torrent_name)

    splitter = ""
    current_best = 0
    min_groups = 3
    for candidate in SPLITTERS:
        groups_test = torrent_name.split(candidate)
        if len(groups_test) >= max(min_groups, current_best):
            current_best = len(groups_test)
            splitter = candidate

    if not splitter:
        return (
            decode_torrent_tags_xxx(torrent_name, tag_types, producer_patterns)
            if try_xxx
            else {"media": ""}
        )

    groups = torrent_name.split(splitter)
    producer = ""
    source = ""
    resolution = ""
    groups_lowered = [group.lower() for group in groups]
    marked: list[int] = []

    for i, group in enumerate(groups_lowered):
        matched = _match_source_token(group)
        if matched:
            source = matched
            marked.append(i)
            break

    for i, group in enumerate(groups_lowered):
        if i in marked:
            continue
        for base in RESOLUTION_BASES:
            if re.fullmatch(base + r"[pi]", group):
                resolution = group
                marked.append(i)
                break
        if resolution:
            break
        if group == "mhd":
            resolution = "mHD"
            marked.append(i)
            break
        if group == "4k":
            nxt = groups_lowered[i + 1] if i + 1 < len(groups_lowered) else ""
            if nxt not in {"remaster", "restoration"}:
                resolution = "2160p"
                marked.append(i)
                break

    if (not source) and (not resolution):
        return (
            decode_torrent_tags_xxx(torrent_name, tag_types, producer_patterns)
            if try_xxx
            else {"media": ""}
        )

    team = ""
    if "team" in tag_types:
        last_item = groups[-1]
        special = find_special_team(last_item, special_teams) or find_special_team(torrent_name, special_teams)
        if special:
            peeled = re.sub(re.escape(special) + r"$", "", last_item, flags=re.IGNORECASE).rstrip("-.")
            groups.pop()
            if peeled:
                groups.append(peeled)
            groups.append(special)
            groups_lowered = [group.lower() for group in groups]
            team = special
            marked.append(len(groups) - 1)
        else:
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

    fmt = ""
    if "format" in tag_types:
        for i, group in enumerate(groups_lowered):
            if i in marked:
                continue
            matched_format = _match_format_token(group)
            if matched_format:
                fmt = matched_format
                marked.append(i)
                break

    process = ""
    if "process" in tag_types:
        lowered = groups_lowered
        if any(group == "remux" for group in lowered):
            process = "Remux"
        elif any(group in RAW_PROCESS_TOKENS for group in lowered) or source == "WEB-DL":
            process = "Raw"
        else:
            process = "Encode"
        for i, group in enumerate(lowered):
            if group == "remux" or group in RAW_PROCESS_TOKENS:
                marked.append(i)

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
        "format": fmt,
        "process": process,
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
