"""The text table is complete and consistent: no key used in the source is missing, both languages
exist, the placeholders match between the languages and match what the call sites pass in."""

import ast
import string
from pathlib import Path

import pytest

from filmdeck import i18n
from filmdeck.core.config import BIT_CHOICES
from filmdeck.strings import STRINGS
from filmdeck.ui.messages import ERROR_CODES

PACKAGE = Path(i18n.__file__).resolve().parent


def _fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def _expand(node: ast.expr) -> list[str]:
    """The literal keys a first argument of tr() can stand for."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.IfExp):
        return _expand(node.body) + _expand(node.orelse)
    if isinstance(node, ast.JoinedStr):                       # f"err.{code}.title"
        text = "".join(p.value if isinstance(p, ast.Constant) else "\0" + ast.unparse(p.value) + "\0"
                       for p in node.values)
        if "\0code\0" in text:
            return [text.replace("\0code\0", c) for c in ERROR_CODES]
        if "\0bits\0" in text:
            return [text.replace("\0bits\0", str(b)) for b in BIT_CHOICES]
    return []


def _calls() -> list[tuple[str, set[str], str]]:
    """(key, passed keyword names, location) for every tr(...) call in the package."""
    found = []
    for path in sorted(PACKAGE.rglob("*.py")):
        if "demo" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr" and node.args:
                keys = _expand(node.args[0])
                names = {k.arg for k in node.keywords if k.arg}
                loc = f"{path.name}:{node.lineno}"
                if not keys and not (isinstance(node.args[0], ast.Name)):
                    pytest.fail(f"cannot determine the key of tr() at {loc}")
                found.extend((k, names, loc) for k in keys)
    return found


def test_both_languages_everywhere():
    for key, entry in STRINGS.items():
        assert set(entry) == {"de", "en"}, key
        assert entry["de"].strip() and entry["en"].strip(), key


def test_same_placeholders_in_both_languages():
    for key, entry in STRINGS.items():
        assert _fields(entry["de"]) == _fields(entry["en"]), key


def test_every_key_used_in_the_source_exists():
    calls = _calls()
    assert len(calls) > 100
    missing = sorted({f"{k} ({loc})" for k, _, loc in calls if k not in STRINGS})
    assert not missing, missing


def test_call_sites_pass_exactly_the_placeholders_of_the_text():
    problems = []
    for key, names, loc in _calls():
        if key not in STRINGS:
            continue
        wanted = _fields(STRINGS[key]["de"])
        if not wanted <= names:
            problems.append(f"{key} at {loc}: text needs {sorted(wanted - names)} that the call does not pass")
    assert not problems, problems


def test_error_codes_have_title_and_text():
    for code in ERROR_CODES:
        assert f"err.{code}.title" in STRINGS and f"err.{code}.text" in STRINGS, code


def test_no_unused_texts():
    used = {k for k, _, _ in _calls()}
    # keys assembled in loops from a table (options.py preview sizes) are named in the source as plain literals
    literals = set()
    for path in PACKAGE.rglob("*.py"):
        if "demo" not in path.parts and path.name != "strings.py":
            literals |= {n.value for n in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
                         if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    unused = sorted(k for k in STRINGS if k not in used and k not in literals)
    assert not unused, unused


def test_tr_falls_back_visibly_and_formats():
    i18n.set_language("en")
    try:
        assert i18n.tr("no.such.key") == "no.such.key"
        assert "7" in i18n.tr("form.size_hint", mb=7)
        i18n.set_language("de")
        assert "MB je Bild" in i18n.tr("form.size_hint", mb=7)
        i18n.set_language("xx")
        assert i18n.language() == "de"
    finally:
        i18n.set_language("de")
