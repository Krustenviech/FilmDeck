"""The driver's margin lines -> where the film opening sits -> the --position-offset that fixes it."""
from filmdeck.core.margins import MarginTracker, refusal_kind

# frames 1, 2 and 4 of a real 600 dpi scan on one 135i (the first scan on a Steam Deck, 2026-11-08)
REAL = """\
INFO of135i: scanning frame 1 @ 600 dpi (dual-light pass)
INFO of135i: computed gain codes (600 dpi dual): R=0x30 G=0x24 B=0x2a
INFO of135i: dual overscan frame 1 (600 dpi): FEEDL=6519 chunks=19 wire_lines=1862 margins lead=0.750 trail=2.374 mm
INFO of135i: positioning to frame 1 (FEEDL=6519, 600 dpi dual)
aperture coverage: VERIFIED (source: ir) — margins lead 0.315 mm, trail 2.972 mm
aperture coverage: WARNING — margin above 2.0 mm (trailing 2.97 mm): the opening found is shorter than the holder's aperture
INFO of135i: scanning frame 2 @ 600 dpi (dual-light pass)
INFO of135i: dual overscan frame 2 (600 dpi): FEEDL=17272 chunks=19 wire_lines=1862 margins lead=0.750 trail=2.446 mm
aperture coverage: VERIFIED (source: ir) — margins lead 0.285 mm, trail 3.062 mm
INFO of135i: scanning frame 4 @ 600 dpi (dual-light pass)
INFO of135i: dual overscan frame 4 (600 dpi): FEEDL=38809 chunks=19 wire_lines=1862 margins lead=0.750 trail=2.696 mm
aperture coverage: NOT verified — IR: leading margin below min_margin_mm (0.15 mm); visible: no aperture found in profile. Kept the full overscan frame(s); no main negative written for this frame.
"""


def feed(text, tracker=None):
    t = tracker or MarginTracker()
    for line in text.splitlines():
        t.feed(line)
    return t


def test_reads_planned_measured_and_refused_frames():
    t = feed(REAL)
    f1, f2, f4 = t.frames[1], t.frames[2], t.frames[4]
    assert (f1.planned_lead, f1.planned_trail, f1.lead, f1.trail, f1.verified) == (0.75, 2.374, 0.315, 2.972, True)
    assert (f2.lead, f2.trail) == (0.285, 3.062)
    assert f4.verified is False and f4.lead is None and f4.planned_trail == 2.696
    assert f4.reason == "IR: leading margin below min_margin_mm (0.15 mm); visible: no aperture found in profile"
    assert refusal_kind(f4.reason) == "lead"


def test_advice_is_the_shift_from_the_model_not_equal_margins():
    a = feed(REAL).advice(0.0)
    # (0.315 - 0.75) - (2.972 - 2.374) = -1.033 -> -0.52 ; frame 2: -0.54 ; mean -0.5
    assert a is not None and a.suggested == -0.5 and a.frames == 2 and a.current == 0.0
    assert -0.55 <= a.low <= a.high <= -0.5
    assert abs(a.shift - (-0.5)) < 1e-9
    # the driver's own "centre the opening" formula would give (0.3 - 3.0) / 2 = -1.4 here: too much at 600 dpi
    assert round((a.lead - a.trail) / 2, 1) == -1.4


def test_advice_builds_on_the_offset_that_was_used():
    t = MarginTracker()
    # the same unit scanned with --position-offset -0.5: margins now equal the plan -> nothing more to change
    feed("INFO of135i: scanning frame 1 @ 600 dpi (dual-light pass)\n"
         "INFO of135i: dual overscan frame 1 (600 dpi): FEEDL=1 chunks=19 wire_lines=1862 margins lead=0.750 trail=2.374 mm\n"
         "aperture coverage: VERIFIED (source: ir) — margins lead 0.790 mm, trail 2.340 mm\n", t)
    assert t.advice(-0.5) is None
    # still 0.5 mm early although -0.5 was used: total -1.0
    t2 = feed("INFO of135i: scanning frame 1 @ 600 dpi (dual-light pass)\n"
              "INFO of135i: dual overscan frame 1 (600 dpi): FEEDL=1 chunks=19 wire_lines=1862 margins lead=0.750 trail=2.374 mm\n"
              "aperture coverage: VERIFIED (source: ir) — margins lead 0.250 mm, trail 2.874 mm\n")
    assert t2.advice(-0.5).suggested == -1.0


def test_small_deviations_and_missing_data_give_no_advice():
    assert MarginTracker().advice(0.0) is None
    small = feed("INFO of135i: scanning frame 1 @ 600 dpi (dual-light pass)\n"
                 "INFO of135i: dual overscan frame 1 (600 dpi): FEEDL=1 chunks=19 wire_lines=1862 margins lead=0.750 trail=2.374 mm\n"
                 "aperture coverage: VERIFIED (source: ir) — margins lead 0.650 mm, trail 2.474 mm\n")
    assert small.advice(0.0) is None            # 0.1 mm is inside the load-to-load spread
    only_refused = feed(REAL.split("INFO of135i: scanning frame 4")[1].join(["INFO of135i: scanning frame 4", ""]))
    assert only_refused.advice(0.0) is None


def test_advice_is_limited_to_what_the_driver_accepts():
    t = feed("INFO of135i: scanning frame 1 @ 600 dpi (dual-light pass)\n"
             "INFO of135i: dual overscan frame 1 (600 dpi): FEEDL=1 chunks=19 wire_lines=1862 margins lead=0.750 trail=2.374 mm\n"
             "aperture coverage: VERIFIED (source: ir) — margins lead 0.200 mm, trail 9.000 mm\n")
    assert t.advice(0.0).suggested == -3.0


def test_a_new_scan_of_a_frame_replaces_its_old_data():
    t = feed(REAL)
    feed("INFO of135i: scanning frame 4 @ 600 dpi (dual-light pass)\n", t)
    assert t.frames[4].verified is None and t.frames[4].reason == ""


def test_refusal_kinds():
    assert refusal_kind("IR: trailing margin below min_margin_mm (0.15 mm)") == "trail"
    assert refusal_kind("leading margin below x; trailing margin below x") == "both"
    assert refusal_kind("IR: aperture not found") == "other"
    assert refusal_kind("empty aperture") == "other"
    # no coverage reason, only the step the frame stopped at (what a cancelled scan leaves behind)
    assert refusal_kind("scan") == "stage" and refusal_kind("not delivered") == "stage"
