"""Turning a session result into words the user can act on."""

from __future__ import annotations

from html import escape

from .. import DRIVER_URL, NEGPY_URL, REPO_URL
from ..core.margins import OffsetAdvice, refusal_kind
from ..core.session import SessionResult
from ..i18n import language, tr

# every code a SessionResult can carry (tests check each has a title and a text in both languages)
ERROR_CODES = (
    "busy", "bad_args", "no_scanner", "no_permission", "no_backend", "no_magazine", "cold", "unsafe_state",
    "load_failed", "interrupted", "scan_failed", "status_failed", "driver_old", "no_space", "no_write",
    "export_failed", "internal",
)


def about_html(version: str, driver_version: str, log_folder: str) -> str:
    """The text of the info box (HTML for a QTextBrowser; every value that is not ours is escaped)."""
    return "".join((
        tr("about.intro", version=escape(version)),
        tr("about.driver", url=DRIVER_URL, version=escape(driver_version or "-")),
        tr("about.project", url=REPO_URL),
        tr("about.ai"),
        tr("about.negpy", url=NEGPY_URL),
        tr("about.logs", folder=escape(log_folder)),
        tr("about.legal"),
    ))


def describe_error(code: str, detail: str = "", version: str = "") -> tuple[str, str]:
    code = code if code in ERROR_CODES else "scan_failed"
    return tr(f"err.{code}.title"), tr(f"err.{code}.text", detail=detail, version=version)


def describe(result: SessionResult, driver_version: str = "") -> tuple[str, str, str]:
    """(level, title, text) with level in ok | warn | error."""
    missing = ", ".join(f"{n:02d}" for n in result.missing)
    if result.kind == "ok":
        return "ok", tr("res.ok.title"), tr("res.ok.text", new=result.images_new, total=result.images_total,
                                           folder=str(result.final_dir))
    if result.kind == "partial":
        return "warn", tr("res.partial.title"), tr("res.partial.text", new=result.images_new, missing=missing or "-",
                                                  folder=str(result.final_dir))
    if result.kind == "cancelled":
        return "warn", tr("res.cancelled.title"), tr("res.cancelled.power" if result.power_cycle else "res.cancelled.text",
                                                    new=result.images_new)
    title, text = describe_error(result.code, result.detail, driver_version)
    if result.power_cycle:
        text += "\n\n" + tr("res.power_cycle_hint")
    if result.images_new:
        text += "\n\n" + tr("res.kept_images", new=result.images_new)
    return "error", title, text


# ----------------------------------------------------------------------------- frames the driver did not crop

def mm(value: float, *, signed: bool = False, decimals: int = 1) -> str:
    """A length in mm for the text: decimal comma in German, a real minus sign."""
    if abs(value) < 0.5 * 10 ** -decimals:
        value = 0.0                                  # no sign (and no "-0.0") for zero
        signed = False
    text = f"{value:+.{decimals}f}" if signed else f"{value:.{decimals}f}"
    text = text.replace("-", "\u2212")
    return text.replace(".", ",") if language() == "de" else text


def _advice_fits(kinds: list[str], advice: OffsetAdvice | None) -> bool:
    """The measured shift must point the way the refusal says: a too small leading margin needs an earlier
    window (lower offset), a too small trailing one a later window."""
    if advice is None:
        return False
    return (("lead" in kinds and advice.suggested < advice.current)
            or ("trail" in kinds and advice.suggested > advice.current))


def describe_missing(result: SessionResult) -> tuple[str, str, OffsetAdvice | None] | None:
    """(title, text, advice to apply or None) for frames that were scanned but not delivered, else None."""
    details = result.missing_details
    if not details:
        return None
    many = len(details) > 1
    numbers = ", ".join(f"{d.number:02d}" for d in details)
    kinds = [refusal_kind(d.reason) for d in details]
    lines = [tr(f"miss.reason.{kind}", number=f"{d.number:02d}", reason=d.reason) for d, kind in zip(details, kinds)]
    lines.append(tr("miss.reserved.many" if many else "miss.reserved.one"))
    paragraphs = ["\n".join(lines)]
    full = [tr("miss.overscan", number=f"{d.number:02d}", file=d.overscan.name) for d in details if d.overscan]
    if full:
        paragraphs.append("\n".join(full))
    advice = result.offset_advice if _advice_fits(kinds, result.offset_advice) else None
    if advice is not None:
        paragraphs.append(tr("miss.advice", shift=mm(abs(advice.shift)), frames=advice.frames,
                             direction=tr("miss.earlier" if advice.shift < 0 else "miss.later"),
                             suggested=mm(advice.suggested, signed=True)))
    elif any(k in ("lead", "trail") for k in kinds):
        paragraphs.append(tr("miss.hint_generic"))
    title = tr("miss.title.many" if many else "miss.title.one", numbers=numbers)
    return title, "\n\n".join(paragraphs), advice
