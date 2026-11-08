"""Keeping the driver up to date.

Checks cgillinger/opticfilm135i-linux for a newer release (or, optionally, a
newer ``master``), shows what changed, and installs it next to the old version.
The previous version stays so a bad update can be rolled back with one click.

Installed versions live in ``<data>/driver/<name>/``; ``current`` is a symlink
to the active one, switched atomically. A new version is started once
(``of135i version``) before it becomes current; if that fails the old one stays.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .. import __version__ as APP_VERSION
from . import paths
from .driver import SOURCE_FILE, parse_version, read_version

log = logging.getLogger(__name__)

REPO = "cgillinger/opticfilm135i-linux"
STATE_FILE = "state.json"


def _api() -> str:
    return os.environ.get("FILMDECK_GITHUB_API", "https://api.github.com").rstrip("/")


def _raw() -> str:
    return os.environ.get("FILMDECK_GITHUB_RAW", "https://raw.githubusercontent.com").rstrip("/")


def _archive() -> str:
    return os.environ.get("FILMDECK_GITHUB_ARCHIVE", "https://github.com").rstrip("/")


class UpdateError(RuntimeError):
    pass


@dataclass(frozen=True)
class Remote:
    kind: str            # "release" | "master"
    ref: str             # tag for a release, commit sha for master
    label: str           # "v0.2.12" or "master 1a2b3c4"
    notes: str           # markdown
    published: str = ""
    sha: str = ""


@dataclass(frozen=True)
class UpdateInfo:
    installed: str       # label of what is installed
    remote: Remote


# --------------------------------------------------------------------- network

def _open(url: str, timeout: float):
    req = urllib.request.Request(url, headers={
        "User-Agent": f"FilmDeck/{APP_VERSION}",
        "Accept": "application/vnd.github+json, text/plain, */*",
    })
    return urllib.request.urlopen(req, timeout=timeout)


def _get_json(url: str, timeout: float = 8.0):
    with _open(url, timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _get_text(url: str, timeout: float = 8.0) -> str | None:
    try:
        with _open(url, timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError):
        return None


# --------------------------------------------------------------------- checking

def latest_tag(timeout: float = 8.0) -> tuple[str, str] | None:
    """(tag, commit sha) of the highest version tag, or None."""
    tags = _get_json(f"{_api()}/repos/{REPO}/tags?per_page=100", timeout)
    best = None
    for t in tags:
        v = parse_version(t.get("name", ""))
        if v is not None and (best is None or v > best[0]):
            best = (v, t["name"], (t.get("commit") or {}).get("sha", ""))
    return (best[1], best[2]) if best else None


def release_notes(tag: str, timeout: float = 8.0) -> str:
    """The release text of ``tag``: the GitHub release body, else the repository's
    ``docs/release-notes-<tag>.md``, else a pointer to the changelog."""
    try:
        body = (_get_json(f"{_api()}/repos/{REPO}/releases/tags/{tag}", timeout).get("body") or "").strip()
        if body:
            return body
    except (urllib.error.URLError, OSError, ValueError):
        pass
    text = _get_text(f"{_raw()}/{REPO}/{tag}/docs/release-notes-{tag}.md", timeout)
    if text and text.strip():
        return text.strip()
    return f"https://github.com/{REPO}/blob/{tag}/CHANGELOG.md"


def check_release(installed_version: str, timeout: float = 8.0) -> UpdateInfo | None:
    """An UpdateInfo when a newer release than ``installed_version`` exists."""
    found = latest_tag(timeout)
    if not found:
        return None
    tag, sha = found
    have, want = parse_version(installed_version), parse_version(tag)
    if want is None or (have is not None and want <= have):
        return None
    remote = Remote("release", tag, tag, release_notes(tag, timeout), sha=sha)
    return UpdateInfo(f"v{installed_version}", remote)


def check_master(installed_source: dict | None, timeout: float = 8.0) -> UpdateInfo | None:
    """An UpdateInfo when ``master`` is ahead of what is installed.

    "Installed" is what FilmDeck recorded at install time: a master sha, or a
    release tag. A driver that was not installed by FilmDeck is compared with
    nothing, so no master update is offered for it.
    """
    if not installed_source:
        return None
    head = _get_json(f"{_api()}/repos/{REPO}/commits/master", timeout)
    sha = head.get("sha", "")
    base = installed_source.get("sha") if installed_source.get("kind") == "master" else installed_source.get("tag")
    if not sha or not base or sha == installed_source.get("sha"):
        return None
    cmp = _get_json(f"{_api()}/repos/{REPO}/compare/{base}...{sha}", timeout)
    commits = cmp.get("commits") or []
    if not commits:
        return None
    lines = []
    for c in reversed(commits[-40:]):
        subject = (c.get("commit", {}).get("message") or "").splitlines()[0]
        if subject:
            lines.append(f"- {subject}")
    installed_label = installed_source.get("label") or str(base)
    remote = Remote("master", sha, f"master {sha[:7]}", "\n".join(lines),
                    published=(head.get("commit", {}).get("committer", {}) or {}).get("date", ""), sha=sha)
    return UpdateInfo(installed_label, remote)


def check(installed_version: str | None, installed_source: dict | None, channel: str,
          timeout: float = 8.0) -> UpdateInfo | None:
    """The update check done at start. Never raises: no network means no update shown."""
    try:
        if channel == "master":
            return check_master(installed_source, timeout)
        if installed_version is None:
            return None
        return check_release(installed_version, timeout)
    except Exception as e:
        log.warning("update check failed (%s): %s: %s", channel, type(e).__name__, e)
        return None


# --------------------------------------------------------------------- install

def _state_path() -> Path:
    return paths.driver_root_dir() / STATE_FILE


def read_state() -> dict:
    try:
        data = json.loads(_state_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_state(state: dict) -> None:
    root = paths.driver_root_dir()
    root.mkdir(parents=True, exist_ok=True)
    tmp = root / (STATE_FILE + ".tmp")
    tmp.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, root / STATE_FILE)


def _switch_current(name: str) -> None:
    root = paths.driver_root_dir()
    link, tmp = root / "current", root / ".current.new"
    if tmp.is_symlink() or tmp.exists():
        tmp.unlink()
    os.symlink(name, tmp)           # relative target: the folder can be moved
    os.replace(tmp, link)


def _safe_extract(archive: Path, dest: Path) -> Path:
    """Unpack a GitHub source archive and return its single top-level folder."""
    dest_resolved = dest.resolve()
    with tarfile.open(archive, "r:gz") as tf:
        for m in tf.getmembers():
            target = (dest / m.name).resolve()
            if dest_resolved not in target.parents and target != dest_resolved:
                raise UpdateError(f"unsafe path in archive: {m.name}")
            if m.issym() or m.islnk():
                link_target = (target.parent / m.linkname).resolve()
                if dest_resolved not in link_target.parents and link_target != dest_resolved:
                    raise UpdateError(f"unsafe link in archive: {m.name}")
            if m.isdev():
                raise UpdateError(f"device file in archive: {m.name}")
        try:
            tf.extractall(dest, filter="data")      # also drops owners and special bits
        except TypeError:                            # older Python without the filter argument
            tf.extractall(dest)                      # the members were checked above
    tops = [p for p in dest.iterdir() if p.is_dir()]
    if len(tops) != 1:
        raise UpdateError("unexpected archive layout")
    return tops[0]


def _download(url: str, target: Path, progress: Callable[[int, int], None] | None) -> None:
    try:
        with _open(url, 30.0) as r, open(target, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
    except (urllib.error.URLError, OSError) as e:
        raise UpdateError(f"download failed: {e}") from e


def install(remote: Remote, *, verify: Callable[[Path], bool] | None = None,
            progress: Callable[[int, int], None] | None = None) -> Path:
    """Download and activate ``remote``; returns the install folder.

    ``verify(folder)`` must return True for the new version to become current.
    """
    name = remote.ref if remote.kind == "release" else f"master-{remote.sha[:7]}"
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise UpdateError(f"refusing odd version name {name!r}")
    root = paths.driver_root_dir()
    root.mkdir(parents=True, exist_ok=True)
    target = root / name
    state = read_state()
    previous_name = state.get("current")

    if not target.is_dir():
        url = (f"{_archive()}/{REPO}/archive/refs/tags/{remote.ref}.tar.gz" if remote.kind == "release"
               else f"{_archive()}/{REPO}/archive/{remote.sha}.tar.gz")
        with tempfile.TemporaryDirectory(dir=root, prefix=".dl-") as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / "src.tar.gz"
            _download(url, archive, progress)
            top = _safe_extract(archive, tmp_path / "x")
            version = read_version(top)
            if version is None:
                raise UpdateError("the download is not the driver (of135i/__init__.py missing)")
            (top / SOURCE_FILE).write_text(json.dumps({
                "kind": remote.kind, "tag": remote.ref if remote.kind == "release" else None,
                "sha": remote.sha or None, "label": remote.label, "version": version,
                "installed_utc": datetime.now(timezone.utc).isoformat(),
            }, indent=2) + "\n", encoding="utf-8")
            os.replace(top, target)

    if verify is not None and not verify(target):
        if previous_name != name:
            shutil.rmtree(target, ignore_errors=True)
        raise UpdateError("the new driver does not start; the old version stays active")

    _switch_current(name)
    log.info("driver installed: %s (previous: %s)", name, previous_name)
    new_state = {"current": name, "previous": previous_name if previous_name != name else state.get("previous")}
    _write_state(new_state)
    _prune(keep={new_state["current"], new_state["previous"]})
    return target


def rollback() -> str:
    """Activate the previous version; returns its name."""
    state = read_state()
    prev = state.get("previous")
    if not prev or not (paths.driver_root_dir() / prev).is_dir():
        raise UpdateError("there is no previous version")
    _switch_current(prev)
    _write_state({"current": prev, "previous": state.get("current")})
    log.info("driver rolled back to %s", prev)
    return prev


def installed_names() -> list[str]:
    root = paths.driver_root_dir()
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir()
                  if p.is_dir() and not p.is_symlink() and (p / SOURCE_FILE).is_file())


def _prune(keep: set[str | None]) -> None:
    root = paths.driver_root_dir()
    for name in installed_names():
        if name not in keep:
            shutil.rmtree(root / name, ignore_errors=True)
