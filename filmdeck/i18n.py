"""German / English texts.

``tr("key", name=value)`` looks the key up in ``strings.STRINGS`` for the current
language. A key that is missing returns the key itself (visible, and the test
suite fails on it), never an exception at run time.
"""

from __future__ import annotations

from .strings import STRINGS

LANGUAGES = ("de", "en")
_current = "de"


def set_language(code: str) -> None:
    global _current
    _current = code if code in LANGUAGES else "de"


def language() -> str:
    return _current


def tr(key: str, **values) -> str:
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(_current) or entry.get("en") or key
    if values:
        try:
            return text.format(**values)
        except (KeyError, IndexError, ValueError):
            return text
    return text
