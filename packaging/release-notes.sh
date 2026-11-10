#!/usr/bin/env bash
# Print the text of a GitHub release for one version: its section from CHANGELOG.md plus a short footer.
#
#   bash packaging/release-notes.sh 0.1.2
#
# Fails (exit 1) when CHANGELOG.md has no "## [VERSION]" section, so a release cannot go out without notes.
set -euo pipefail

VERSION="${1:?usage: release-notes.sh VERSION (without the leading v)}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

section="$(awk -v v="$VERSION" '
    /^## \[/ { if (on) exit; on = (index($0, "## [" v "]") == 1); next }
    on { print }
' "$ROOT/CHANGELOG.md")"

# drop leading blank lines (trailing ones go with the command substitution)
section="$(printf '%s\n' "$section" | sed '/./,$!d')"
[ -n "$section" ] || { echo "CHANGELOG.md has no section for $VERSION" >&2; exit 1; }

# absolute links on GitHub (a release page does not resolve relative ones reliably), relative when run locally
if [ -n "${GITHUB_REPOSITORY:-}" ]; then
    BASE="${GITHUB_SERVER_URL:-https://github.com}/$GITHUB_REPOSITORY"
else
    BASE="../.."
fi

cat <<EOF
$section

---

**Install:** download \`FilmDeck-$VERSION-x86_64.AppImage\`, make it executable (\`chmod +x\`) and start it. Steps for the Steam Deck and for other x86_64 Linux systems, including the one-time USB permission, are in the [README]($BASE/blob/v$VERSION/README.md) ([Deutsch]($BASE/blob/v$VERSION/README.de.md)).

**Made with AI** (Claude, by Anthropic) together with the repository owner. Tried on one Steam Deck only; see the Status table in the README for what is and is not tested on a real scanner.
EOF
