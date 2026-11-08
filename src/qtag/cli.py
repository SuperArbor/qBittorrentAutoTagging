"""Command-line entry for qtag."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from qtag import __version__
from qtag.client import process_all, process_new
from qtag.config import (
    CONFIG_FILENAME,
    STATISTICS_FILENAME,
    default_config_dir,
    dump_yaml,
    load_config,
    load_statistics,
    write_default_config,
)
from qtag.tagging import prune_statistics

logger = logging.getLogger("qtag")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="qtag",
        description="为 qBittorrent 中的种子自动设置分类与标签。",
    )
    parser.add_argument(
        "info_hash",
        nargs="?",
        help="种子 info hash。省略时处理客户端中的全部种子。",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        help="config.yaml 与 statistics.yaml 所在目录。默认使用系统配置目录。",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="写入一份默认 config.yaml 后退出。",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="输出调试日志。",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"qtag {__version__}",
    )
    return parser


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)
    config_dir = (args.config_dir or default_config_dir()).expanduser().resolve()
    config_path = config_dir / CONFIG_FILENAME

    if args.init:
        created = write_default_config(config_path, overwrite=False)
        if created:
            logger.info("Wrote default config to %s", config_path)
        else:
            logger.info("Config already exists at %s", config_path)
        return 0

    if not config_path.exists():
        write_default_config(config_path, overwrite=False)
        logger.error("No config found. A template was written to %s", config_path)
        logger.error("Edit host/port/username/password, then run qtag again.")
        return 1

    config = load_config(config_dir)
    statistics = load_statistics(config_dir)

    if args.info_hash:
        logger.info(
            "Running process_new with update_tags %s",
            "on" if config.get("update_tags") else "off",
        )
        process_new(args.info_hash, config, statistics)
        return 0

    logger.info(
        "Running process_all with update_tags %s and update_statistics %s",
        "on" if config.get("update_tags") else "off",
        "on" if config.get("update_statistics") else "off",
    )
    logger.info("Handling all torrents...")
    statistics = process_all(config, statistics)
    if config.get("update_statistics"):
        logger.info("Updating statistics...")
        dump_yaml(config_dir / STATISTICS_FILENAME, prune_statistics(statistics))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
