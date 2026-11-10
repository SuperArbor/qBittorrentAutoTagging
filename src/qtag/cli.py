"""Command-line entry for qtag."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

from qtag import __version__
from qtag.client import process_all, process_new
from qtag.config import load_config, resolve_config_path, write_default_config
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
        "--config",
        type=Path,
        help="配置文件，或 config.yaml 所在目录。默认使用系统配置目录。",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="写入一份默认 config.yaml 后退出。",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="扫描全部种子，把分类/标签统计打印到控制台（不写文件、不改客户端）。",
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


def configure_logging(verbose: bool, *, quiet: bool = False) -> None:
    if quiet and not verbose:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    logging.basicConfig(
        stream=sys.stderr,
        level=level,
        format="%(levelname)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose, quiet=args.report)
    config_path = resolve_config_path(args.config)

    if args.init:
        created = write_default_config(config_path, overwrite=False)
        if created:
            logger.info("Wrote default config to %s", config_path)
        else:
            logger.info("Config already exists at %s", config_path)
        return 0

    if args.report and args.info_hash:
        logger.error("Do not pass an info hash together with --report.")
        return 2

    if not config_path.exists():
        write_default_config(config_path, overwrite=False)
        logger.error("No config found. A template was written to %s", config_path)
        logger.error("Edit qbittorrent host/port/username/password, then run qtag again.")
        return 1

    config = load_config(config_path)

    if args.report:
        statistics = process_all(config, mutate=False, collect_statistics=True)
        print(
            yaml.safe_dump(prune_statistics(statistics), allow_unicode=True, sort_keys=False),
            end="",
        )
        return 0

    if args.info_hash:
        logger.info("Running process_new")
        process_new(args.info_hash, config)
        return 0

    logger.info("Handling all torrents...")
    process_all(config, mutate=True, collect_statistics=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
