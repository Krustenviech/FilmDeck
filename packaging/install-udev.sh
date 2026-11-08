#!/usr/bin/env bash
# Allow the logged-in user to use the Plustek OpticFilm 135i (USB 07b3:1436) without root.
# Run once, as your normal user (it asks for your password through sudo):
#
#   bash install-udev.sh [path/to/60-of135i.rules]
#
# Without an argument it takes the rule from the driver that FilmDeck downloaded.
# Afterwards unplug the scanner's USB cable and plug it in again (or power-cycle the scanner).
set -euo pipefail

NAME="60-of135i.rules"
DIR="${UDEV_RULES_DIR:-/etc/udev/rules.d}"          # overridable for testing
SRC="${1:-}"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/filmdeck/driver"

if [ -z "$SRC" ]; then
    for candidate in "$DATA/current/udev/$NAME"; do
        [ -f "$candidate" ] && SRC="$candidate" && break
    done
fi

TMP=""
if [ -z "$SRC" ]; then
    echo "The driver's rule file was not found (start FilmDeck once so it can download the driver)."
    echo "Using the built-in copy of the rule instead."
    TMP="$(mktemp)"
    trap 'rm -f "$TMP"' EXIT
    cat > "$TMP" <<'RULE'
# Plustek OpticFilm 135i (07b3:1436) - grant the logged-in console user access
SUBSYSTEM=="usb", ATTRS{idVendor}=="07b3", ATTRS{idProduct}=="1436", MODE="0660", TAG+="uaccess"
RULE
    SRC="$TMP"
fi
[ -f "$SRC" ] || { echo "rule file not found: $SRC" >&2; exit 1; }

echo "Rule:        $SRC"
echo "Installing:  $DIR/$NAME"
grep -v '^#' "$SRC" | sed 's/^/    /'

SUDO=""
[ "$(id -u)" -eq 0 ] || SUDO="sudo"

reenable=""
if ! $SUDO install -Dm644 "$SRC" "$DIR/$NAME" 2>/dev/null; then
    if command -v steamos-readonly >/dev/null 2>&1; then
        echo "The system drive is write-protected (SteamOS). Unlocking it for this one step ..."
        $SUDO steamos-readonly disable
        reenable=1
        trap '[ -n "$reenable" ] && $SUDO steamos-readonly enable; rm -f "$TMP"' EXIT
        $SUDO install -Dm644 "$SRC" "$DIR/$NAME"
    else
        echo "Could not write to $DIR." >&2
        exit 1
    fi
fi

if command -v udevadm >/dev/null 2>&1; then
    $SUDO udevadm control --reload-rules
    $SUDO udevadm trigger
fi
echo
echo "Done. Now unplug the scanner's USB cable and plug it in again."
