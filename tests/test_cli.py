import logging
from pathlib import Path

from qtag.cli import main


def test_init_writes_config(tmp_path: Path, caplog):
    with caplog.at_level(logging.INFO):
        code = main(["--init", "--config-dir", str(tmp_path)])
    assert code == 0
    assert (tmp_path / "config.yaml").exists()
    assert "Wrote default config" in caplog.text


def test_missing_config_writes_template_and_exits(tmp_path: Path):
    code = main(["--config-dir", str(tmp_path)])
    assert code == 1
    assert (tmp_path / "config.yaml").exists()


def test_report_rejects_info_hash(tmp_path: Path):
    main(["--init", "--config-dir", str(tmp_path)])
    code = main(["--report", "abc", "--config-dir", str(tmp_path)])
    assert code == 2
