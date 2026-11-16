#!/bin/sh
# Install the coffee command from this checkout.
set -eu
ROOT=$(CDPATH= cd -P "$(dirname "$0")" && pwd)
if [ "$(uname -s)" != Darwin ] || [ ! -x /usr/bin/caffeinate ]; then
    echo 'coffee-cat requires macOS and /usr/bin/caffeinate.' >&2
    exit 1
fi
command -v python3 >/dev/null 2>&1 || {
    echo 'Install Python 3 first (for example: brew install python).' >&2
    exit 1
}
BIN="$HOME/.local/bin"
mkdir -p "$BIN"
if [ -d "$BIN/coffee" ]; then
    echo "$BIN/coffee is a directory; cannot install the launcher." >&2
    exit 1
fi
ln -sf "$ROOT/coffee.py" "$BIN/coffee"
echo "Installed $BIN/coffee"
echo 'Keep this checkout in place and include ~/.local/bin in PATH.'
