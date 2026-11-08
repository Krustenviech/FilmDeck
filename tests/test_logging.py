"""What ends up in the logs: the app log (filmdeck.log) and the per-scan log files."""
import logging

from filmdeck.core import driver as drv
from filmdeck.core import paths, update
from filmdeck.core import session as sess
from filmdeck.core.config import Settings
from test_session import Run


def messages(caplog):
    return "\n".join(r.getMessage() for r in caplog.records)


def test_scanner_check_and_driver_are_logged(demo, caplog):
    caplog.set_level(logging.INFO)
    d = drv.locate(Settings())
    assert sess.check_scanner(d).ok
    text = messages(caplog)
    assert "driver: " in text and "(demo)" in text
    assert "scanner check: rc=0 ok=True" in text


def test_eject_is_logged(demo, caplog):
    caplog.set_level(logging.INFO)
    assert sess.eject_holder(drv.locate(Settings())).ok
    assert "eject: ok" in messages(caplog)


def test_failed_eject_is_logged_as_error(demo, caplog):
    demo.setenv("OF135I_DEMO_SCENARIO", "eject_fail")
    caplog.set_level(logging.INFO)
    assert not sess.eject_holder(drv.locate(Settings())).ok
    assert any(r.levelno == logging.ERROR and "eject: failed" in r.getMessage() for r in caplog.records)


def test_update_failure_is_logged_not_raised(monkeypatch, caplog):
    monkeypatch.setenv("FILMDECK_GITHUB_API", "http://127.0.0.1:9")
    caplog.set_level(logging.INFO)
    assert update.check("0.2.11", None, "release", timeout=1) is None
    assert "update check failed (release)" in messages(caplog)


def test_scan_result_is_in_the_scan_log_and_the_app_log(tmp_path, demo, caplog):
    caplog.set_level(logging.INFO)
    settings = Settings(scan_dir=str(tmp_path / "scans"), preview_size=0)
    res = Run(settings, "strip", "26-11-Test-Cam", frames=[1, 2]).go()
    assert res.kind == "ok"
    logs = sorted(paths.log_dir().glob("[0-9]*-26-11-Test-Cam.log"))
    assert len(logs) == 1
    content = logs[0].read_text(encoding="utf-8")
    assert content.count("$ ") >= 1                                   # the driver command line
    assert "== result: kind=ok" in content and "images=2" in content
    assert "scan 26-11-Test-Cam: == result: kind=ok" in messages(caplog)


def test_old_scan_logs_are_pruned_but_the_app_log_stays(tmp_path, demo):
    log_dir = paths.log_dir()
    log_dir.mkdir(parents=True)
    (log_dir / "filmdeck.log").write_text("app log\n", encoding="utf-8")
    for i in range(sess.LOG_KEEP + 5):
        (log_dir / f"2026010{i // 10}-0000{i % 10}0-old{i:02d}.log").write_text("x", encoding="utf-8")
    settings = Settings(scan_dir=str(tmp_path / "scans"), preview_size=0)
    assert Run(settings, "strip", "26-11-Test-Cam", frames=[1]).go().kind == "ok"
    scan_logs = sorted(p.name for p in log_dir.glob("[0-9]*-*.log"))
    assert len(scan_logs) == sess.LOG_KEEP
    assert (log_dir / "filmdeck.log").read_text(encoding="utf-8") == "app log\n"
