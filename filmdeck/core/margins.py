"""What the driver says about where the film opening sits in the scan window.

For every frame the driver prints the margins it *planned* between the opening and the edges of the
scan window, and, after the scan, the margins it *measured* (``aperture coverage: VERIFIED ... margins
lead X mm, trail Y mm``). On one scanner the holder can sit a fraction of a millimetre away from the
position the driver's model assumes. Then the measured leading margin is smaller than planned and the
trailing one larger by the same amount, and a frame whose leading margin falls below 0.15 mm is refused.
``--position-offset`` moves every window; this module works out the value from the measured deviation.

This text is only used for advice. What a scan produced is always taken from the files, never from here.

The deviation (measured - planned) is used, not the difference of the two measured margins: the driver
rounds the window length up to whole chunks, so at low resolutions the trailing margin is planned much
larger than the leading one, and "equal margins" would over-correct (600 dpi: about 1.4 mm instead of 0.5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

OFFSET_LIMIT_MM = 3.0       # the driver refuses more than +/-3 mm
STEP_MM = 0.1
REFUSAL_KINDS = ("lead", "trail", "both", "other")
MIN_CHANGE_MM = 0.2         # a smaller correction is within the load-to-load spread: no advice

_NUM = r"(\d+(?:\.\d+)?)"
_SCANNING = re.compile(r"\bscanning frame (\d+) @")
_PLANNED = re.compile(r"\boverscan frame (\d+) \(\d+ dpi\):.*\bmargins lead=" + _NUM + r" trail=" + _NUM + r" mm")
_MEASURED = re.compile(r"^aperture coverage: VERIFIED\b.*?margins lead " + _NUM + r" mm, trail " + _NUM + r" mm")
_REFUSED = re.compile(r"^aperture coverage: NOT verified\s*[—-]\s*(.*?)\.\s+Kept the full overscan")


@dataclass
class FrameMargins:
    frame: int
    planned_lead: float | None = None
    planned_trail: float | None = None
    lead: float | None = None
    trail: float | None = None
    verified: bool | None = None
    reason: str = ""

    def deviation(self) -> float | None:
        """The offset this frame alone suggests, on top of the one in use (negative = start the window earlier)."""
        if None in (self.planned_lead, self.planned_trail, self.lead, self.trail) or not self.verified:
            return None
        return ((self.lead - self.planned_lead) - (self.trail - self.planned_trail)) / 2.0


@dataclass(frozen=True)
class OffsetAdvice:
    current: float                  # the offset the scan used (mm)
    suggested: float                # the offset to use instead (mm), rounded to 0.1
    frames: int                     # how many frames it is based on
    low: float                      # smallest and largest per-frame suggestion (mm, absolute values)
    high: float
    lead: float                     # mean measured / planned margins of those frames (mm)
    trail: float
    planned_lead: float
    planned_trail: float

    @property
    def shift(self) -> float:
        """How far the opening sits from where the driver expects it (negative = earlier)."""
        return self.suggested - self.current


@dataclass
class MarginTracker:
    """Fed with the driver's output lines of one or more strips."""

    frames: dict[int, FrameMargins] = field(default_factory=dict)
    _current: int | None = None

    def _frame(self, number: int) -> FrameMargins:
        return self.frames.setdefault(number, FrameMargins(number))

    def feed(self, line: str) -> None:
        m = _SCANNING.search(line)
        if m:
            self._current = int(m[1])
            self.frames[self._current] = FrameMargins(self._current)    # a new scan of this number replaces the old
            return
        m = _PLANNED.search(line)
        if m:
            f = self._frame(int(m[1]))
            f.planned_lead, f.planned_trail = float(m[2]), float(m[3])
            self._current = f.frame
            return
        if self._current is None:
            return
        m = _MEASURED.match(line)
        if m:
            f = self._frame(self._current)
            f.lead, f.trail, f.verified = float(m[1]), float(m[2]), True
            return
        m = _REFUSED.match(line)
        if m:
            f = self._frame(self._current)
            f.verified, f.reason = False, m[1].strip()

    def advice(self, current_offset: float = 0.0) -> OffsetAdvice | None:
        """The offset that would put the opening where the driver expects it, or None when there is nothing
        to measure or the change would be too small to matter."""
        used = [f for f in self.frames.values() if f.deviation() is not None]
        if not used:
            return None
        devs = [f.deviation() for f in used]
        mean = sum(devs) / len(devs)
        suggested = round(round((current_offset + mean) / STEP_MM) * STEP_MM, 3)
        suggested = max(-OFFSET_LIMIT_MM, min(OFFSET_LIMIT_MM, suggested))
        if abs(suggested - current_offset) < MIN_CHANGE_MM - 1e-9:
            return None
        n = len(used)
        return OffsetAdvice(
            current=current_offset, suggested=suggested, frames=n,
            low=round(current_offset + min(devs), 2), high=round(current_offset + max(devs), 2),
            lead=sum(f.lead for f in used) / n, trail=sum(f.trail for f in used) / n,
            planned_lead=sum(f.planned_lead for f in used) / n, planned_trail=sum(f.planned_trail for f in used) / n)


def refusal_kind(reason: str) -> str:
    """One of REFUSAL_KINDS: which margin the driver's reason says was too small ("other": none of them)."""
    r = reason.lower()
    lead, trail = "leading margin below" in r, "trailing margin below" in r
    if lead and trail:
        return "both"
    if lead:
        return "lead"
    if trail:
        return "trail"
    return "other"
