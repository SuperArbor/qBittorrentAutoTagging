"""Talk to qBittorrent and apply tags."""

from __future__ import annotations

import logging
from typing import Any

import qbittorrentapi as qbit

from qtag.config import prepare_runtime
from qtag.tagging import (
    FILE_MEDIA,
    TAGS,
    UNKNOWN_TAG,
    classify_format_by_files,
    classify_media_by_files,
    decode_torrent_tags,
    filter_by_when,
    prefix_tags,
    tagging_strategy,
)

logger = logging.getLogger(__name__)


def _connect(config: dict[str, Any]) -> qbit.Client:
    qbt = config["qbittorrent"]
    return qbit.Client(
        host=qbt["host"],
        port=qbt["port"],
        username=qbt["username"],
        password=qbt["password"],
    )


def torrent_file_names(torrent: qbit.TorrentDictionary) -> list[str]:
    try:
        return [item.name for item in torrent.files]
    except Exception:
        logger.warning("Could not list files for torrent %s", torrent.name)
        return []


def match_category(tracker_urls: list[str], trackers: dict[str, dict]) -> str:
    for url in tracker_urls:
        lowered = url.lower()
        for category, spec in trackers.items():
            url_key = str(spec.get("url_key") or "")
            if url_key and url_key.lower() in lowered:
                return category
    return ""


def write_torrent_tags(
    torrent: qbit.TorrentDictionary,
    tags_ui: dict[str, str],
    manual_tags: list[str],
) -> None:
    current_tags = [tag.strip() for tag in torrent["tags"].split(",") if tag.strip()]
    to_remove = [tag for tag in current_tags if tag not in manual_tags]
    if to_remove:
        torrent.remove_tags(to_remove)
    to_add = [tag for tag in tags_ui.values() if tag]
    if to_add:
        torrent.add_tags(to_add)
    logger.info("tags: %s", to_add)


def tags_for_torrent(
    torrent: qbit.TorrentDictionary,
    category: str,
    trackers: dict[str, dict],
    auto_tags: dict[str, dict],
    teams: list[str],
) -> dict[str, str]:
    media_types = trackers[category]["media"] if category else None
    strategy = tagging_strategy(media_types)
    if strategy == "music":
        tags = {"media": "Music"}
        if "format" in auto_tags:
            tags["format"] = classify_format_by_files(torrent_file_names(torrent))
        return tags
    if strategy == "files":
        media = classify_media_by_files(torrent_file_names(torrent), torrent.name)
        tags = {"media": media}
        if media in FILE_MEDIA and "format" in auto_tags:
            tags["format"] = classify_format_by_files(torrent_file_names(torrent))
        return tags
    try_xxx = bool(category) and "XXX" in trackers[category]["media"]
    return decode_torrent_tags(
        torrent.name,
        teams=teams,
        tag_types=list(auto_tags),
        try_xxx=try_xxx,
        special_teams=list((auto_tags.get("team") or {}).get("special") or []),
    )


def handle_torrent(
    torrent: qbit.TorrentDictionary,
    category: str,
    runtime: dict[str, Any],
    teams: list[str],
    delay_operation: bool,
    *,
    mutate: bool = True,
) -> tuple[dict[str, str], dict[str, str]]:
    tags = tags_for_torrent(
        torrent=torrent,
        category=category,
        trackers=runtime["trackers"],
        auto_tags=runtime["auto_tags"],
        teams=teams,
    )
    tags = filter_by_when(tags, runtime["auto_tags"])
    tags_ui = prefix_tags(tags, runtime["auto_tags"])
    if mutate and not delay_operation:
        write_torrent_tags(torrent, tags_ui, runtime["manual_tags"])
    return tags, tags_ui


def _record_statistics(
    tags: dict[str, str],
    category: str,
    auto_tags: dict[str, dict],
    statistics_total: dict,
    statistics_categories: dict,
) -> None:
    if category and category not in statistics_categories:
        statistics_categories[category] = {name: {} for name in auto_tags}
    for tag_type, raw_value in tags.items():
        if tag_type not in auto_tags:
            continue
        if not raw_value:
            if tag_type != "media":
                continue
            tag_value = UNKNOWN_TAG
        else:
            tag_value = raw_value
        statistics_total.setdefault(tag_type, {})
        statistics_total[tag_type][tag_value] = statistics_total[tag_type].get(tag_value, 0) + 1
        if category:
            statistics_categories[category].setdefault(tag_type, {})
            bucket = statistics_categories[category][tag_type]
            bucket[tag_value] = bucket.get(tag_value, 0) + 1


def init_statistics(auto_tags: dict[str, dict], statistics: dict[str, Any]) -> tuple[dict, dict]:
    statistics_total = statistics.get("TOTAL") or {}
    statistics_categories = statistics.get("CATEGORIES") or {}
    dynamic_types = {"team", "year", "producer"}

    for tag_type in auto_tags:
        if tag_type == "team":
            previous = list((statistics_total.get(tag_type) or {}).keys())
            statistics_total[tag_type] = {name: 0 for name in previous}
            for category in statistics_categories:
                statistics_categories[category][tag_type] = {name: 0 for name in previous}
        elif tag_type in dynamic_types or tag_type not in TAGS:
            statistics_total[tag_type] = {}
            for category in statistics_categories:
                statistics_categories[category][tag_type] = {}
        else:
            statistics_total[tag_type] = {name: 0 for name in TAGS[tag_type]}
            for category in statistics_categories:
                statistics_categories[category][tag_type] = {name: 0 for name in TAGS[tag_type]}

    for tag_type in list(statistics_total):
        if tag_type not in auto_tags and tag_type != "team":
            statistics_total[tag_type] = {}
    for category in statistics_categories:
        for tag_type in list(statistics_categories[category]):
            if tag_type not in auto_tags and tag_type != "team":
                statistics_categories[category][tag_type] = {}

    return statistics_total, statistics_categories


def process_new(info_hash: str, config: dict[str, Any]) -> None:
    runtime = prepare_runtime(config)
    teams: list[str] = []
    client = _connect(config)
    try:
        client.auth_log_in()
        logger.info("Fetching specified torrent from the client...")
        torrent_list = client.torrents_info(torrent_hashes=info_hash)
        if not torrent_list:
            logger.info("Torrent with hash %s unfound, skip it", info_hash)
            return

        torrent = torrent_list[0]
        category = match_category([tracker.url for tracker in torrent.trackers], runtime["trackers"])
        if category:
            if category not in client.torrent_categories.categories:
                client.torrents_create_category(category)
            if torrent["category"] != category:
                torrent.set_category(category)
            logger.info("category: %s", category)

        ignored = {name for name, spec in runtime["trackers"].items() if spec["ignore"]}
        if category in ignored:
            logger.info("Torrent %s in a tracker specified to ignore, skip tagging it", torrent.name)
            return

        logger.info("Handling tags for torrent %s...", torrent.name)
        handle_torrent(torrent, category, runtime, teams, delay_operation=False)
    except qbit.LoginFailed:
        logger.exception("qBittorrent login failed")
    finally:
        try:
            client.auth_log_out()
        except Exception:
            pass


def process_all(
    config: dict[str, Any],
    *,
    mutate: bool = True,
    collect_statistics: bool = False,
) -> dict[str, Any]:
    runtime = prepare_runtime(config)
    auto_tags = runtime["auto_tags"]
    trackers = runtime["trackers"]
    statistics_total, statistics_categories = init_statistics(auto_tags, {"TOTAL": {}, "CATEGORIES": {}})
    delay_operation = mutate and any(spec["max_number"] > 0 for spec in auto_tags.values())
    logger.info("Running %s delay operation mode", "with" if delay_operation else "without")

    client = _connect(config)
    torrent_tags: dict[str, dict[str, str]] = {}
    try:
        client.auth_log_in()
        if mutate:
            for category in trackers:
                if category not in client.torrent_categories.categories:
                    client.torrents_create_category(category)

        logger.info("Fetching all the torrents from the client...")
        torrent_list = client.torrents_info()
        total = len(torrent_list)
        logger.info("Done. %s torrents to process.", total)

        tracker_category_map: dict[str, str] = {}
        ignored = {name for name, spec in trackers.items() if spec["ignore"]}
        teams = list(statistics_total.get("team") or {})

        for count, torrent in enumerate(torrent_list, start=1):
            tracker_url = torrent["tracker"]
            if tracker_url and tracker_url in tracker_category_map:
                category = tracker_category_map[tracker_url]
            else:
                category = match_category([item.url for item in torrent.trackers], trackers)
                if tracker_url and category:
                    tracker_category_map[tracker_url] = category

            if category:
                if mutate and torrent["category"] != category:
                    torrent.set_category(category)
                logger.info("category: %s", category)

            if category in ignored:
                logger.info(
                    "(%s / %s) Torrent %s in a tracker specified to ignore, skip tagging it",
                    count,
                    total,
                    torrent.name,
                )
                continue

            delayed = "[Delayed] " if delay_operation else ""
            logger.info("(%s / %s) %sHandling tags for torrent %s...", count, total, delayed, torrent.name)
            tags, tags_ui = handle_torrent(
                torrent, category, runtime, teams, delay_operation, mutate=mutate
            )
            if delay_operation:
                torrent_tags[torrent.hash] = tags_ui or {}
            if collect_statistics:
                _record_statistics(tags, category, auto_tags, statistics_total, statistics_categories)

        if mutate:
            if delay_operation:
                _apply_delayed_tags(client, torrent_tags, runtime)
            _delete_unused_tags(client)
    except qbit.LoginFailed:
        logger.exception("qBittorrent login failed")
    finally:
        try:
            client.auth_log_out()
        except Exception:
            pass

    return {"TOTAL": statistics_total, "CATEGORIES": statistics_categories}


def _apply_delayed_tags(client: qbit.Client, torrent_tags: dict[str, dict[str, str]], runtime: dict[str, Any]) -> None:
    logger.info("Delay operation starts: updating tags...")
    auto_tags = runtime["auto_tags"]
    tag_type_tags = {name: set() for name in auto_tags}
    tag_numbers: dict[str, int] = {}
    for tags_ui in torrent_tags.values():
        for tag_type, tag in tags_ui.items():
            if not tag:
                continue
            tag_numbers[tag] = tag_numbers.get(tag, 0) + 1
            if tag_type in tag_type_tags:
                tag_type_tags[tag_type].add(tag)

    tags_to_remove: list[str] = []
    for tag_type, values in tag_type_tags.items():
        tags_of_type = list(values)
        limit = auto_tags[tag_type]["max_number"]
        if limit > 0 and limit < len(tags_of_type):
            tags_of_type.sort(key=lambda tag: tag_numbers[tag], reverse=True)
            tags_to_remove.extend(tags_of_type[limit:])

    manual_tags = runtime["manual_tags"]
    tags_to_remove = [tag for tag in tags_to_remove if tag not in manual_tags]
    total = len(torrent_tags)
    for count, (info_hash, tags_ui) in enumerate(torrent_tags.items(), start=1):
        torrent = client.torrents_info(torrent_hashes=info_hash)[0]
        logger.info("(%s / %s) Tagging torrent %s...", count, total, torrent.name)
        filtered = {key: value for key, value in tags_ui.items() if value not in tags_to_remove}
        write_torrent_tags(torrent, filtered, manual_tags)


def _delete_unused_tags(client: qbit.Client) -> None:
    logger.info("Remove unneeded tags (those used by no torrents)...")
    tags_to_delete = [tag for tag in client.torrents_tags() if not client.torrents_info(tag=tag)]
    if tags_to_delete:
        client.torrents_delete_tags(tags=tags_to_delete)
