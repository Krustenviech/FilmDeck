#!/usr/bin/env bash
# Build FilmDeck-<version>-x86_64.AppImage
#
#   packaging/build-appimage.sh            build, then run the built-in selftest on the result
#   NO_SELFTEST=1 packaging/build-appimage.sh
#
# What it does: unpacks a relocatable Python (python-build-standalone), installs FilmDeck and its
# dependencies into it, adds libusb, and packs everything with appimagetool. Needs: bash, curl, tar,
# sha256sum, libusb-1.0 on this machine (Debian/Ubuntu: libusb-1.0-0, Arch: libusb), internet access.
# The scanner driver (of135i) is NOT inside the AppImage; the program downloads it on first start.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
BUILD="${BUILD_DIR:-$HERE/build}"

# Pinned downloads. The Python hash is the one in the release's own SHA256SUMS file; the appimagetool
# hash is the file as it was when this script was tested.
PY_TAG="20251014"
PY_FILE="cpython-3.12.12+${PY_TAG}-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz"
PY_SHA256="c74addcd1b033a6e4d60ead3ab47fcc995569027e01d3061c4a934f363c4a0cf"
PY_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PY_TAG}/${PY_FILE//+/%2B}"
TOOL_VERSION="1.9.1"
TOOL_SHA256="ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0"
TOOL_URL="https://github.com/AppImage/appimagetool/releases/download/${TOOL_VERSION}/appimagetool-x86_64.AppImage"

VERSION="$(sed -n 's/^__version__ *= *"\(.*\)"/\1/p' "$ROOT/filmdeck/__init__.py")"
[ -n "$VERSION" ] || { echo "cannot read the version from filmdeck/__init__.py" >&2; exit 1; }
OUT="$BUILD/FilmDeck-${VERSION}-x86_64.AppImage"

fetch() {   # fetch URL FILE SHA256
    local url="$1" file="$2" sum="$3"
    if [ -f "$file" ] && echo "$sum  $file" | sha256sum -c --status; then return; fi
    echo "downloading $(basename "$file") ..."
    curl -fsSL --retry 3 -o "$file.part" "$url"
    mv "$file.part" "$file"
    echo "$sum  $file" | sha256sum -c --status || { echo "checksum mismatch for $file" >&2; rm -f "$file"; exit 1; }
}

mkdir -p "$BUILD/cache"
fetch "$PY_URL" "$BUILD/cache/$PY_FILE" "$PY_SHA256"
fetch "$TOOL_URL" "$BUILD/cache/appimagetool-$TOOL_VERSION" "$TOOL_SHA256"
chmod +x "$BUILD/cache/appimagetool-$TOOL_VERSION"

# libusb: the scanner cannot be reached without it, and SteamOS may not have it.
LIBUSB="$(ldconfig -p 2>/dev/null | awk '/libusb-1\.0\.so\.0 .*x86-64/ {print $NF; exit}')"
[ -n "$LIBUSB" ] && [ -e "$LIBUSB" ] || { echo "libusb-1.0 not found on this machine (install libusb-1.0-0 / libusb)" >&2; exit 1; }

APPDIR="$BUILD/AppDir"
rm -rf "$APPDIR" "$BUILD/src"
mkdir -p "$APPDIR/usr/lib" "$BUILD/src"
tar -xzf "$BUILD/cache/$PY_FILE" -C "$APPDIR/usr"          # -> AppDir/usr/python
PY="$APPDIR/usr/python/bin/python3"

# install from a copy of the sources so the checkout stays clean
cp -r "$ROOT/filmdeck" "$ROOT/pyproject.toml" "$ROOT/README.md" "$BUILD/src/"
find "$BUILD/src" -name __pycache__ -type d -prune -exec rm -rf {} +
"$PY" -m pip install --disable-pip-version-check --no-warn-script-location --quiet "$BUILD/src"

# trim what the program never loads (the selftest below proves the rest still works)
SITE="$("$PY" -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
for d in qml translations metatypes; do rm -rf "$SITE/PySide6/Qt/$d"; done
for d in include typesystems glue scripts examples; do rm -rf "$SITE/PySide6/$d"; done
rm -rf "$SITE/PySide6/Qt/libexec" "$SITE"/PySide6/{assistant,designer,linguist,lupdate,lrelease,uic,rcc,svgtoqml,qmllint,qmlformat,qmlls}* 2>/dev/null || true
find "$APPDIR/usr/python" -name tests -type d -path '*site-packages*' -prune -exec rm -rf {} + 2>/dev/null || true
rm -rf "$APPDIR/usr/python/share" "$APPDIR/usr/python/include"

cp -L "$LIBUSB" "$APPDIR/usr/lib/libusb-1.0.so.0"

cat > "$APPDIR/AppRun" <<'RUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
export APPDIR="$HERE"
export PATH="$HERE/usr/python/bin:$PATH"
export LD_LIBRARY_PATH="$HERE/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONNOUSERSITE=1
unset PYTHONHOME PYTHONPATH
exec "$HERE/usr/python/bin/python3" -m filmdeck "$@"
RUN
chmod +x "$APPDIR/AppRun"

install -Dm644 "$HERE/filmdeck.desktop" "$APPDIR/filmdeck.desktop"
install -Dm644 "$HERE/filmdeck.desktop" "$APPDIR/usr/share/applications/filmdeck.desktop"
install -Dm644 "$HERE/filmdeck.svg" "$APPDIR/filmdeck.svg"
install -Dm644 "$HERE/filmdeck.svg" "$APPDIR/usr/share/icons/hicolor/scalable/apps/filmdeck.svg"
ln -sf filmdeck.svg "$APPDIR/.DirIcon"

rm -f "$OUT"
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$BUILD/cache/appimagetool-$TOOL_VERSION" --no-appstream "$APPDIR" "$OUT"
chmod +x "$OUT"
echo
echo "built: $OUT ($(du -h "$OUT" | cut -f1))"

if [ -z "${NO_SELFTEST:-}" ]; then
    echo "running the selftest on the built AppImage ..."
    APPIMAGE_EXTRACT_AND_RUN=1 "$OUT" --selftest
fi
