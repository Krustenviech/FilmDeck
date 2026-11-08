
import pytest

from filmdeck.core import driver as drv
from filmdeck.core import session as sess
from filmdeck.core.config import Settings


class Run:
    """Runs a ScanSession against the demo driver and answers its questions like a user."""

    def __init__(self, settings, mode, name="film", next_answers=(), frames=None, next_frames=(), **kw):
        self.events = []
        self.answers = list(next_answers)
        self.next_frames = list(next_frames)
        self.on_frame = None
        self.s = sess.ScanSession(settings, drv.locate(settings), name, mode, self.listener,
                                  frames=frames, free_bytes=kw.pop("free_bytes", lambda p: 1 << 40), **kw)

    def listener(self, ev):
        self.events.append(ev)
        if ev.kind == "prompt":
            self.s.answer_prompt()
        elif ev.kind == "ask_next":
            self.s.answer_next(self.answers.pop(0) if self.answers else False,
                               self.next_frames.pop(0) if self.next_frames else None)
        elif ev.kind == "frame_written" and self.on_frame:
            self.on_frame(ev)

    def go(self, timeout=60):
        self.s.start()
        self.s.join(timeout)
        assert not self.s.running, "session did not finish"
        return self.s.result

    def kinds(self, kind):
        return [e.data for e in self.events if e.kind == kind]


@pytest.fixture
def settings(tmp_path, demo):
    return Settings(scan_dir=str(tmp_path / "scans"), preview_size=160)


def names(folder):
    return sorted(p.name for p in folder.iterdir() if not p.name.startswith("."))


def test_strip_three_frames(settings):
    r = Run(settings, "strip", "26-11-Kodak_Gold-F3", frames=[1, 2, 3])
    res = r.go()
    assert res.kind == "ok" and res.images_total == 3 and res.images_new == 3 and res.strips == 1
    assert not res.missing and not res.power_cycle and not res.warnings
    folder = settings.scan_root() / "26-11-Kodak_Gold-F3"
    assert names(folder) == [f"26-11-Kodak_Gold-F3_0{i}{suf}.tiff" for i in (1, 2, 3) for suf in ("", "_ir")]
    assert [p["frame"] for p in r.kinds("frame_written")] == [1, 2, 3]
    assert len(r.kinds("prompt")) == 1 and r.kinds("prompt")[0]["prompt_kind"] == "reinsert"
    assert [e.data["state"] for e in r.events if e.kind == "state"] == ["preflight", "scanning", "exporting"]
    assert r.kinds("strip_started") == [{"strip": 1, "frames": 3, "frame_numbers": [1, 2, 3], "full_load": True}]
    assert r.kinds("finished")[0]["result"] is res


def test_bw_has_no_ir_and_respects_bit_depth(settings):
    settings.film_type, settings.bit_depth = "bw", 16
    res = Run(settings, "strip", "bw", frames=[1, 2]).go()
    assert res.kind == "ok"
    assert names(settings.scan_root() / "bw") == ["bw_01.tiff", "bw_02.tiff"]
    import tifffile
    assert tifffile.imread(str(settings.scan_root() / "bw" / "bw_01.tiff")).ndim == 2


def test_second_strip_into_same_folder_continues_numbering(settings):
    assert Run(settings, "strip", "film", frames=[1, 2]).go().images_new == 2
    assert sess.existing_images(settings.scan_root(), "film") == 2
    res = Run(settings, "strip", "film", frames=[1, 2]).go()
    assert res.images_total == 4 and res.images_new == 2
    assert "film_04.tiff" in names(settings.scan_root() / "film")


def test_film_mode_two_strips_with_next_strip_load(settings):
    r = Run(settings, "film", "film", next_answers=[True, False])
    res = r.go()
    assert res.kind == "ok" and res.strips == 2 and res.images_total == 12
    assert [s["full_load"] for s in r.kinds("strip_started")] == [True, False]
    assert len(r.kinds("prompt")) == 1               # the second strip needs no reinsert
    assert [d["images"] for d in r.kinds("strip_done")] == [6, 12]
    assert (settings.scan_root() / "film" / "film_12.tiff").exists()


def test_film_mode_short_last_strip(settings, monkeypatch):
    monkeypatch.setenv("OF135I_DEMO_SCENARIO", "empty_from:3")
    res = Run(settings, "film", "film", next_answers=[True, False]).go()
    assert res.kind == "ok" and res.images_total == 4 and res.strips == 2


def test_cold_scanner_falls_back_to_full_load(settings, monkeypatch):
    monkeypatch.setenv("OF135I_DEMO_SCENARIO", "cold")
    r = Run(settings, "film", "film", next_answers=[True, False], frames=None)
    res = r.go()
    assert res.kind == "ok" and res.images_total == 12
    assert len(r.kinds("prompt")) == 2 and [s["full_load"] for s in r.kinds("strip_started")] == [True, True]


def test_fast_next_strip_off_uses_full_load(settings):
    settings.fast_next_strip = False
    r = Run(settings, "film", "film", next_answers=[True, False])
    assert r.go().strips == 2 and len(r.kinds("prompt")) == 2


@pytest.mark.parametrize("scenario,code,power", [
    ("no_scanner", "no_scanner", False), ("no_permission", "no_permission", False),
    ("no_magazine", "no_magazine", False), ("unsafe", "unsafe_state", True), ("busy", "busy", False)])
def test_preflight_failures_start_nothing(settings, monkeypatch, scenario, code, power):
    monkeypatch.setenv("OF135I_DEMO_SCENARIO", scenario)
    r = Run(settings, "strip", "film", frames=[1, 2])
    res = r.go()
    assert (res.kind, res.code, res.power_cycle) == ("error", code, power)
    assert not r.kinds("strip_started") and not r.kinds("prompt")


def test_scan_failure_keeps_delivered_frames_and_demands_power_cycle(settings, monkeypatch):
    monkeypatch.setenv("OF135I_DEMO_SCENARIO", "scan_fail:2")
    res = Run(settings, "strip", "film", frames=[1, 2, 3]).go()
    assert (res.kind, res.code, res.power_cycle) == ("error", "scan_failed", True)
    assert res.images_total == 1 and (settings.scan_root() / "film" / "film_01.tiff").exists()
    assert "Power the scanner OFF" in res.detail


def test_coverage_failure_is_partial(settings, monkeypatch):
    monkeypatch.setenv("OF135I_DEMO_SCENARIO", "coverage_fail:2")
    res = Run(settings, "strip", "film", frames=[1, 2, 3]).go()
    assert res.kind == "partial" and res.missing == [2] and res.images_total == 2 and not res.power_cycle


def test_cancel_during_scan(settings, monkeypatch):
    monkeypatch.setenv("OF135I_DEMO_SPEED", "0.4")
    r = Run(settings, "strip", "film", frames=[1, 2, 3, 4])
    r.on_frame = lambda ev: r.s.cancel() if ev.data["frame"] == 1 else None
    res = r.go()
    assert res.kind == "cancelled" and res.power_cycle and res.images_total == 1


def test_cancel_while_waiting_for_the_next_strip(settings):
    r = Run(settings, "film", "film")
    r.listener = lambda ev: (r.events.append(ev), r.s.answer_prompt() if ev.kind == "prompt" else None,
                             r.s.cancel() if ev.kind == "ask_next" else None)
    r.s._listener = r.listener
    res = r.go()
    assert res.kind == "ok" and res.strips == 1 and not res.power_cycle and res.images_total == 6


def test_driver_too_old_and_no_space_and_unwritable(settings, tmp_path):
    old = drv.Driver(drv.demo_root(), "0.2.10", managed=False, demo=True)
    s = sess.ScanSession(settings, old, "film", "strip", lambda e: None)
    s.start(); s.join(20)
    assert s.result.code == "driver_old"
    res = Run(settings, "strip", "film", frames=[1, 2], free_bytes=lambda p: 10).go()
    assert res.code == "no_space"
    blocker = tmp_path / "file"
    blocker.write_text("x")
    settings.scan_dir = str(blocker / "sub")
    assert Run(settings, "strip", "film", frames=[1]).go().code == "no_write"


def test_settings_are_snapshotted(settings):
    r = Run(settings, "strip", "film", frames=[1])
    settings.dpi = 7200
    assert r.s.settings.dpi == 3600


def test_estimate_and_existing():
    assert sess.estimate_bytes(3600, 6) > 1_000_000_000
    assert sess.estimate_bytes(7200, 6) == pytest.approx(4 * sess.estimate_bytes(3600, 6), rel=0.001)


def test_strip_mode_rejects_bad_mode(settings):
    with pytest.raises(ValueError):
        sess.ScanSession(settings, drv.locate(settings), "x", "bogus", lambda e: None)


# ---------------------------------------------------------------- chosen frames, eject

def test_frames_spec_compresses_ranges():
    assert drv.frames_spec([1, 2, 3]) == "1-3" and drv.frames_spec([6, 1, 2]) == "1-2,6"
    assert drv.frames_spec([4]) == "4" and drv.frames_spec([1, 3, 5]) == "1,3,5" and drv.frames_spec(range(1, 7)) == "1-6"
    for bad in ([], [0], [7], [1, 9]):
        with pytest.raises(ValueError):
            drv.frames_spec(bad)


def test_only_the_chosen_frames_are_scanned_and_numbered_without_gaps(settings):
    r = Run(settings, "strip", "film", frames=[2, 3, 6])
    res = r.go()
    assert res.kind == "ok" and res.images_total == 3
    assert [p["frame"] for p in r.kinds("frame_written")] == [2, 3, 6]
    assert r.kinds("strip_started")[0]["frame_numbers"] == [2, 3, 6]
    assert sorted(p.name for p in (settings.scan_root() / "film").glob("film_0?.tiff")) == [
        "film_01.tiff", "film_02.tiff", "film_03.tiff"]


def test_film_mode_each_strip_has_its_own_frames(settings):
    r = Run(settings, "film", "film", frames=[3, 4], next_answers=[True, True, False], next_frames=[[1, 2, 3], [1]])
    res = r.go()
    assert res.kind == "ok" and res.strips == 3 and res.images_total == 2 + 3 + 1
    assert [s["frame_numbers"] for s in r.kinds("strip_started")] == [[3, 4], [1, 2, 3], [1]]


def test_film_mode_next_strip_defaults_to_all_six(settings):
    r = Run(settings, "film", "film", frames=[5], next_answers=[True, False])
    assert r.go().images_total == 1 + 6
    assert r.kinds("strip_started")[1]["frame_numbers"] == [1, 2, 3, 4, 5, 6]


def test_session_rejects_frames_outside_the_holder(settings):
    with pytest.raises(ValueError):
        Run(settings, "strip", "film", frames=[7])


def test_eject_ok(settings):
    res = sess.eject_holder(drv.locate(settings), timeout=30)
    assert res.ok and "ejected" in res.detail and not res.power_cycle


@pytest.mark.parametrize("scenario,code,power", [
    ("unsafe", "unsafe_state", True), ("no_scanner", "no_scanner", False), ("busy", "busy", False),
    ("eject_fail", "scan_failed", True)])
def test_eject_failures(settings, monkeypatch, scenario, code, power):
    monkeypatch.setenv("OF135I_DEMO_SCENARIO", scenario)
    res = sess.eject_holder(drv.locate(settings), timeout=30)
    assert (res.ok, res.code, res.power_cycle) == (False, code, power)
    assert res.detail


def test_eject_that_never_ends_is_interrupted_not_killed():
    calls = []

    class Stuck:
        def __init__(self, argv, env, **kw):
            self.argv = argv

        def start(self):
            calls.append("start")

        def wait(self, timeout=None):
            calls.append(f"wait {timeout}")
            return None if len(calls) == 2 else 130

        def interrupt(self):
            calls.append("interrupt")

        def output(self):
            return "ejecting ..."

    res = sess.eject_holder(_fake_driver(), runner_cls=Stuck, timeout=5)
    assert calls == ["start", "wait 5", "interrupt", "wait 60.0"] and "kill" not in calls
    assert (res.ok, res.code, res.power_cycle) == (False, "interrupted", True)


def _fake_driver():
    from pathlib import Path
    return drv.Driver(Path("/nonexistent"), "0.2.11", False)
