"""Reading the driver's console output.

Only used for live progress and for naming a failure. What a scan produced is
always taken from the files (the album index), never from this text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# The prompt of ``of135i load`` / ``digitize`` (of135i/loadflow.py REINSERT_PROMPT).
# It is written without a trailing newline, so it is looked for in the partial line.
REINSERT_MARKER = "Press Enter when it is at the stop"

_WROTE_MAIN = re.compile(r"^wrote (?P<path>.+?[/\\]f(?P<frame>\d+)\.tiff) \(")
_ROLL_HEADER = re.compile(r"^=== digitize roll (?P<roll>\d+) -> (?P<dir>.+) ===$")
_STOPPING = re.compile(r"^stopping: (?P<why>.*)$")
_ROLL_DONE = re.compile(r"^roll (?P<roll>\d+) done: (?P<frames>\d+) frames")
_PROBLEM = re.compile(r"^(error|refused|FAILED|warning):", re.IGNORECASE)


@dataclass(frozen=True)
class Line:
    kind: str                      # wrote_main roll_header stopping roll_done ejected load_jog load_seq load_done problem text
    data: dict = field(default_factory=dict)


def classify_line(line: str) -> Line:
    m = _WROTE_MAIN.match(line)
    if m:
        return Line("wrote_main", {"frame": int(m["frame"]), "path": m["path"]})
    m = _ROLL_HEADER.match(line)
    if m:
        return Line("roll_header", {"roll": int(m["roll"]), "dir": m["dir"]})
    m = _STOPPING.match(line)
    if m:
        return Line("stopping", {"why": m["why"]})
    m = _ROLL_DONE.match(line)
    if m:
        return Line("roll_done", {"roll": int(m["roll"]), "frames": int(m["frames"])})
    if line.strip() == "ejected":
        return Line("ejected")
    if line.startswith("running the vendor app-start jog"):
        return Line("load_jog")
    if line.startswith("running the vendor load sequence"):
        return Line("load_seq")
    if line.startswith("load sequence completed"):
        return Line("load_done")
    if _PROBLEM.match(line):
        return Line("problem", {"text": line})
    return Line("text")


def needs_power_cycle(text: str, rc: int) -> bool:
    """The driver fails closed: after most failures only a power cycle of the scanner helps."""
    t = text.lower()
    return (rc == 130
            or "power the scanner off" in t
            or "power cycle" in t
            or "power-cycle" in t
            or "restarting this program is not sufficient" in t)


def classify_failure(rc: int, text: str) -> tuple[str, bool]:
    """(error code, needs_power_cycle) for a command that ended with ``rc`` != 0."""
    t = text.lower()
    power = needs_power_cycle(text, rc)
    if rc == 3:
        return "busy", False
    if rc == 2:
        return "bad_args", False
    if "not found on the host usb bus" in t:
        return "no_scanner", False
    if "access denied" in t or "errno 13" in t or "insufficient permissions" in t:
        return "no_permission", False
    if "no backend available" in t or "nobackenderror" in t:
        return "no_backend", False
    if "no magazine present in the slot" in t:
        return "no_magazine", False
    if "scanner is cold" in t and "--next-strip" in t:
        return "cold", False
    if "unsafe" in t and "start state" in t:
        return "unsafe_state", True
    if "load feed did not engage" in t or "next-strip load feed did not engage" in t:
        return "load_failed", True
    if rc == 130:
        return "interrupted", True
    return "scan_failed", power


@dataclass(frozen=True)
class ScannerStatus:
    ok: bool                       # the status command ran
    magazine: bool | None          # sensor reports a magazine
    start_state: str | None        # "idle-homed" | "cold-never-homed" | "unsafe"
    error: str | None              # error code from classify_failure when not ok
    power_cycle: bool
    raw: str


def parse_status(rc: int, stdout: str, stderr: str) -> ScannerStatus:
    text = stdout + "\n" + stderr
    if rc != 0:
        code, power = classify_failure(rc, text)
        if code == "scan_failed":
            code = "status_failed"
        return ScannerStatus(False, None, None, code, power, text.strip())
    magazine = None
    if "magazine: sensor reports present" in stdout:
        magazine = True
    elif "magazine: not detected" in stdout:
        magazine = False
    state = None
    m = re.search(r"start state:\s*(\S+)", stdout)
    if m:
        state = m.group(1)
    return ScannerStatus(True, magazine, state, None, state == "unsafe", text.strip())
