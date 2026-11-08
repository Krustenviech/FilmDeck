"""Turning a session result into words the user can act on."""

from __future__ import annotations

from ..core.session import SessionResult
from ..i18n import tr

# every code a SessionResult can carry (tests check each has a title and a text in both languages)
ERROR_CODES = (
    "busy", "bad_args", "no_scanner", "no_permission", "no_backend", "no_magazine", "cold", "unsafe_state",
    "load_failed", "interrupted", "scan_failed", "status_failed", "driver_old", "no_space", "no_write",
    "export_failed", "internal",
)


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
