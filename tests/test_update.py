import io
import json
import tarfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from filmdeck.core import driver as drv
from filmdeck.core import paths, update
from filmdeck.core.config import Settings

REPO = update.REPO


def make_tar(version="0.2.12", extra=None, with_driver=True) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        def add(name, data: bytes):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
        if with_driver:
            add(f"opticfilm135i-linux-{version}/of135i/__init__.py", f'__version__ = "{version}"\n'.encode())
            add(f"opticfilm135i-linux-{version}/README.md", b"x")
        for name, data in (extra or {}).items():
            add(name, data)
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    routes: dict = {}

    def do_GET(self):
        path = self.path.split("?")[0]
        hit = self.routes.get(path)
        if hit is None:
            self.send_response(404)
            self.end_headers()
            return
        body = hit if isinstance(hit, bytes) else json.dumps(hit).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


@pytest.fixture
def server(monkeypatch):
    Handler.routes = {}
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    monkeypatch.setenv("FILMDECK_GITHUB_API", base)
    monkeypatch.setenv("FILMDECK_GITHUB_RAW", base)
    monkeypatch.setenv("FILMDECK_GITHUB_ARCHIVE", base)
    yield Handler.routes
    srv.shutdown()


def tags(*names):
    return [{"name": n, "commit": {"sha": "abc" + n}} for n in names]


def test_release_check(server):
    server[f"/repos/{REPO}/tags"] = tags("v0.2.10", "v0.2.12", "v0.2.9", "nightly", "v0.2.11", "v0.2.12-rc1")
    server[f"/repos/{REPO}/releases/tags/v0.2.12"] = {"body": "## New\n- fixed stop gate"}
    info = update.check_release("0.2.11")
    assert info.remote.ref == "v0.2.12" and info.installed == "v0.2.11"
    assert info.remote.notes == "## New\n- fixed stop gate"
    assert update.check_release("0.2.12") is None and update.check_release("0.3.0") is None


def test_notes_fallbacks(server):
    server[f"/repos/{REPO}/tags"] = tags("v0.2.12")
    server[f"/{REPO}/v0.2.12/docs/release-notes-v0.2.12.md"] = b"# notes from the docs folder\n"
    assert update.check_release("0.2.11").remote.notes == "# notes from the docs folder"
    del server[f"/{REPO}/v0.2.12/docs/release-notes-v0.2.12.md"]
    assert "CHANGELOG.md" in update.check_release("0.2.11").remote.notes


def test_check_never_raises(monkeypatch):
    monkeypatch.setenv("FILMDECK_GITHUB_API", "http://127.0.0.1:9")     # nothing listens there
    assert update.check("0.2.11", None, "release", timeout=1) is None
    assert update.check(None, None, "release", timeout=1) is None


def install_release(server, version, verify=None, **tar):
    tag = f"v{version}"
    server[f"/{REPO}/archive/refs/tags/{tag}.tar.gz"] = make_tar(version, **tar)
    remote = update.Remote("release", tag, tag, "notes")
    return update.install(remote, verify=verify)


def test_install_switch_prune_rollback(server):
    assert drv.locate(Settings()) is None
    install_release(server, "0.2.12")
    d = drv.locate(Settings())
    assert d.managed and d.version == "0.2.12" and d.source["tag"] == "v0.2.12" and not d.too_old
    assert (paths.driver_root_dir() / "current").is_symlink()
    install_release(server, "0.2.13")
    assert drv.locate(Settings()).version == "0.2.13"
    assert update.installed_names() == ["v0.2.12", "v0.2.13"]
    install_release(server, "0.2.14")
    assert update.installed_names() == ["v0.2.13", "v0.2.14"]        # the oldest one is pruned
    assert update.rollback() == "v0.2.13" and drv.locate(Settings()).version == "0.2.13"
    assert update.read_state() == {"current": "v0.2.13", "previous": "v0.2.14"}


def test_reinstalling_current_keeps_previous(server):
    install_release(server, "0.2.12")
    install_release(server, "0.2.13")
    install_release(server, "0.2.13")
    assert update.read_state() == {"current": "v0.2.13", "previous": "v0.2.12"}


def test_failed_verify_keeps_old_version(server):
    install_release(server, "0.2.12")
    with pytest.raises(update.UpdateError, match="old version stays"):
        install_release(server, "0.2.13", verify=lambda folder: False)
    assert drv.locate(Settings()).version == "0.2.12"
    assert update.installed_names() == ["v0.2.12"] and update.read_state()["current"] == "v0.2.12"


def test_unsafe_archive_is_refused(server):
    with pytest.raises(update.UpdateError, match="unsafe"):
        install_release(server, "0.2.12", extra={"../evil.txt": b"x"})
    assert not (paths.driver_root_dir() / "evil.txt").exists() and update.installed_names() == []
    assert not list(paths.driver_root_dir().glob(".dl-*"))            # temp folder cleaned up


def test_not_a_driver_and_download_errors(server):
    with pytest.raises(update.UpdateError, match="not the driver"):
        install_release(server, "0.2.12", with_driver=False, extra={"opticfilm135i-linux-0.2.12/x": b"1"})
    with pytest.raises(update.UpdateError, match="download failed"):
        update.install(update.Remote("release", "v9.9.9", "v9.9.9", ""))
    with pytest.raises(update.UpdateError, match="odd version"):
        update.install(update.Remote("release", "../x", "x", ""))
    with pytest.raises(update.UpdateError, match="no previous"):
        update.rollback()


def test_master_channel(server):
    sha = "1234567890abcdef"
    server[f"/repos/{REPO}/commits/master"] = {"sha": sha, "commit": {"committer": {"date": "2026-11-05T10:00:00Z"}}}
    server[f"/repos/{REPO}/compare/v0.2.12...{sha}"] = {"commits": [
        {"commit": {"message": "Fix A\n\nlong body"}}, {"commit": {"message": "Add B"}}]}
    info = update.check("0.2.12", {"kind": "release", "tag": "v0.2.12", "label": "v0.2.12"}, "master")
    assert info.installed == "v0.2.12" and info.remote.label == "master 1234567"
    assert info.remote.notes == "- Add B\n- Fix A"
    assert update.check("0.2.12", None, "master") is None                      # not installed by us: nothing to compare
    assert update.check("0.2.12", {"kind": "master", "sha": sha, "tag": None}, "master") is None
    server[f"/{REPO}/archive/{sha}.tar.gz"] = make_tar("0.2.13")
    target = update.install(info.remote)
    assert target.name == "master-1234567" and drv.locate(Settings()).source["sha"] == sha
