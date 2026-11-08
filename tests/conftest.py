import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """No test may touch the real configuration, data or driver install."""
    monkeypatch.setenv("FILMDECK_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("FILMDECK_DEMO", raising=False)
    return tmp_path / "home"


@pytest.fixture
def demo(monkeypatch, tmp_path):
    """Run the demo driver (fast, with its own 'scanner loaded' state)."""
    monkeypatch.setenv("FILMDECK_DEMO", "1")
    monkeypatch.setenv("OF135I_DEMO_STATE", str(tmp_path / "demo-state"))
    monkeypatch.setenv("OF135I_DEMO_SPEED", "0.01")
    monkeypatch.delenv("OF135I_DEMO_SCENARIO", raising=False)
    return monkeypatch


def make_demo_stage(tmp_path, monkeypatch, *, album="film", frames="1-3", dpi=600, ir=True, strips=1):
    """Run the demo driver the way the session does and return (stage dir, album)."""
    import subprocess
    from filmdeck.core import driver as drv
    from filmdeck.core.config import Settings
    monkeypatch.setenv("FILMDECK_DEMO", "1")
    monkeypatch.setenv("OF135I_DEMO_STATE", str(tmp_path / "demo-state"))
    monkeypatch.setenv("OF135I_DEMO_SPEED", "0")
    d = drv.locate(Settings())
    stage = tmp_path / "stage"
    for i in range(strips):
        opts = drv.DigitizeOptions(str(stage), album, frames, dpi, ir, assume_loaded=i > 0)
        argv = drv.digitize_argv(opts)
        if i == 0:
            p = subprocess.run(argv, env=drv.environment(d), input="\n", capture_output=True, text=True)
        else:
            subprocess.run(drv.load_argv(True), env=drv.environment(d), capture_output=True, text=True)
            p = subprocess.run(argv, env=drv.environment(d), capture_output=True, text=True)
        assert p.returncode == 0, p.stderr + p.stdout
    return stage, album


@pytest.fixture(autouse=True, scope="session")
def sigint_not_ignored():
    """A parent that ignores SIGINT passes that on to the driver, and then 'abort' would do nothing.
    The real program resets it at start (filmdeck/__main__.py)."""
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
