import logging
from pathlib import Path

from qtag.cli import main
from qtag.config import resolve_config_path, write_default_config


def test_init_writes_config(tmp_path: Path, caplog):
    with caplog.at_level(logging.INFO):
        code = main(["--init", "--config", str(tmp_path)])
    assert code == 0
    assert (tmp_path / "config.yaml").exists()
    assert "Wrote default config" in caplog.text


def test_init_writes_named_config_file(tmp_path: Path):
    cfg = tmp_path / "config-remote.yaml"
    code = main(["--init", "--config", str(cfg)])
    assert code == 0
    assert cfg.is_file()
    assert not (tmp_path / "config.yaml").exists()


def test_missing_config_writes_template_and_exits(tmp_path: Path):
    code = main(["--config", str(tmp_path)])
    assert code == 1
    assert (tmp_path / "config.yaml").exists()


def test_existing_config_file_is_loaded(tmp_path: Path, monkeypatch):
    cfg = tmp_path / "config-remote.yaml"
    write_default_config(cfg)
    monkeypatch.setattr("qtag.cli.process_all", lambda *args, **kwargs: {})
    code = main(["--config", str(cfg)])
    assert code == 0
    assert not (cfg / "config.yaml").exists()


def test_resolve_config_path_file_and_dir(tmp_path: Path):
    cfg = tmp_path / "config-remote.yaml"
    cfg.write_text("x: 1", encoding="utf-8")
    assert resolve_config_path(cfg) == cfg.resolve()
    assert resolve_config_path(tmp_path) == (tmp_path / "config.yaml").resolve()
    missing = tmp_path / "other.yaml"
    assert resolve_config_path(missing) == missing.resolve()


def test_report_rejects_info_hash(tmp_path: Path):
    main(["--init", "--config", str(tmp_path)])
    code = main(["--report", "abc", "--config", str(tmp_path)])
    assert code == 2
