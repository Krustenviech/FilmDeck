"""Checks against the REAL driver source (skipped when it is not around).

    OF135I_SRC=/path/to/opticfilm135i-linux  pytest tests/test_contract_real_driver.py

Needs pyusb (the driver imports it). Nothing here touches USB.
"""

import itertools
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SRC = os.environ.get("OF135I_SRC")
pytestmark = pytest.mark.skipif(not SRC or not (Path(SRC) / "of135i" / "cli.py").is_file(),
                                reason="OF135I_SRC not set")


@pytest.fixture(scope="module")
def real():
    pytest.importorskip("usb")
    sys.path.insert(0, SRC)
    for name in [m for m in sys.modules if m == "of135i" or m.startswith("of135i.")]:
        del sys.modules[name]
    import of135i.cli as cli
    import of135i.digitize as digitize
    import of135i.loadflow as loadflow
    yield type("Real", (), {"cli": cli, "digitize": digitize, "loadflow": loadflow})
    sys.path.remove(SRC)


def test_driver_version_is_supported():
    from filmdeck.core import driver as drv
    version = drv.read_version(Path(SRC))
    assert drv.parse_version(version) >= drv.MIN_VERSION


def test_every_digitize_command_we_can_build_is_accepted(real):
    from filmdeck.core import driver as drv
    parser = real.cli.build_parser()
    base = len(drv.base_argv())
    combos = itertools.product((600, 1200, 2400, 3600, 7200), (True, False), (True, False), (0, 90, 180, 270),
                               (True, False), (None, 0.0, -0.4, 1.25), (True, False), ([1], [1, 2], [1, 2, 3, 4, 5, 6], [2, 3, 4, 5, 6], [1, 2, 6], [3, 5]))
    seen = 0
    for dpi, ir, dust, rot, cal, offset, assume, picked in combos:
        o = drv.DigitizeOptions("/tmp/stage dir", "26-11-Kodak_Gold-F3", drv.frames_spec(picked), dpi, ir, dust,
                                rot, cal, offset, assume)
        a = parser.parse_args(drv.digitize_argv(o)[base:])
        assert a.command == "digitize" and a.dpi == dpi and a.ir is ir and a.rotate == rot
        assert a.album == "26-11-Kodak_Gold-F3" and a.out == "/tmp/stage dir"
        assert a.assume_loaded is assume and a.no_cal_data is (not cal)
        assert a.no_clean is (ir and not dust)
        assert a.position_offset == offset
        assert real.cli._parse_frames(a.frames) == picked
        # defaults we rely on: negative output, stop gate enforced, stop at an empty opening
        assert not a.positive and a.cal_wait_scanstop == "enforce" and not a.no_stop_at_empty and not a.sweep
        assert not a.force and not a.recalibrate
        seen += 1
    assert seen == 5 * 2 * 2 * 4 * 2 * 4 * 2 * 6


def test_load_commands_are_accepted(real):
    from filmdeck.core import driver as drv
    parser = real.cli.build_parser()
    base = len(drv.base_argv())
    assert parser.parse_args(drv.load_argv(True)[base:]).next_strip is True
    assert parser.parse_args(drv.load_argv(False)[base:]).next_strip is False
    for argv in (drv.status_argv(), drv.version_argv(), drv.doctor_argv()):
        assert parser.parse_args(argv[base:]).command == argv[-1]


def test_names_we_produce_are_valid_album_names(real):
    from filmdeck.core import naming
    import datetime as dt
    for film, cam in (("Kodak Gold", "Nikon F3"), ("Harman Phoenix II", ""), ("", ""), ("Ilford HP5+", "Leica M6")):
        name = naming.compose_name(film, cam, dt.date(2026, 11, 7))
        assert real.digitize.check_album_name(name) == name


def test_text_we_parse_still_exists_in_the_driver():
    """Prompts and messages FilmDeck reacts to, found in the driver's source."""
    from filmdeck.core.parser import REINSERT_MARKER
    root = Path(SRC) / "of135i"
    loadflow = (root / "loadflow.py").read_text()
    cli = (root / "cli.py").read_text()
    assert REINSERT_MARKER in loadflow.replace('"\n    "', "")        # string is split over source lines
    for needle in ("magazine: sensor reports present", "magazine: not detected", "start state:",
                   "not found on the host USB bus", "no magazine present in the slot", "running the vendor load sequence",
                   "load sequence completed", "ejected", "stopping: empty aperture", "COLD", "--next-strip"):
        assert needle in cli or needle in loadflow or needle in (root / "usbio.py").read_text(), needle
    assert 'f"wrote {out} ({vis_c.shape[1]}x{vis_c.shape[0]}, 16-bit RGB, "' in cli
    assert "=== digitize roll" in cli and "Power the scanner OFF" in (root / "safety.py").read_text() + cli


def test_exit_code_meanings_match():
    root = Path(SRC) / "of135i"
    safety = (root / "safety.py").read_text()
    assert "EXIT_BUSY = 3" in safety


@pytest.mark.parametrize("scenario", ["", "empty_from:3", "coverage_fail:2", "empty_from:2,coverage_fail:1"])
def test_demo_album_matches_the_real_album_logic(real, tmp_path, monkeypatch, scenario):
    """The demo driver must lay out manifest and album like the real one: compare with the real album_plan."""
    from filmdeck.core import driver as drv
    from filmdeck.core.config import Settings
    monkeypatch.setenv("FILMDECK_DEMO", "1")
    monkeypatch.setenv("OF135I_DEMO_STATE", str(tmp_path / "st"))
    monkeypatch.setenv("OF135I_DEMO_SPEED", "0")
    if scenario:
        monkeypatch.setenv("OF135I_DEMO_SCENARIO", scenario)
    d = drv.locate(Settings())
    stage = tmp_path / "stage"
    for i in range(2):
        if i:
            subprocess.run(drv.load_argv(True), env=drv.environment(d), capture_output=True, text=True)
        argv = drv.digitize_argv(drv.DigitizeOptions(str(stage), "film", "1-4", 600, True, assume_loaded=bool(i)))
        subprocess.run(argv, env=drv.environment(d), input="\n", capture_output=True, text=True)
    index = json.loads((stage / "film" / "index.json").read_text())
    real_items = real.digitize.album_plan(str(stage), "film")
    strip = lambda items: [{k: v for k, v in it.items() if k != "diag"} for it in items]
    assert index["images"] == strip(real_items)
    # and the real album_sync produces the same index content and numbered files
    real_index = real.digitize.album_sync(str(stage), "film")
    assert real_index["images"] == index["images"] and real_index["delivered"] == index["delivered"]
    assert real_index["missing"] == index["missing"]


def test_eject_command_is_accepted(real):
    from filmdeck.core import driver as drv
    parser = real.cli.build_parser()
    a = parser.parse_args(drv.eject_argv()[len(drv.base_argv()):])
    assert a.command == "eject"
