# coffee-cat

A sleepy animated coffee cat in your terminal that keeps your Mac awake.
The command is `coffee`.

## Install

Requires macOS and Python 3. The player uses only the Python standard library
and macOS's built-in `caffeinate`.

```sh
git clone https://github.com/the-sides/coffee-cat.git
cd coffee-cat
./install.sh
coffee
```

Include `~/.local/bin` in your `PATH`. The installer links `coffee` to this
checkout, so keep the checkout in place. When using jOS, run this directory's
installer instead of cloning again.

## Usage

```sh
coffee                  # prevent system sleep while on AC power
coffee -d               # prevent display sleep
coffee -sd              # prevent both
coffee -t 3600          # quit after an hour
coffee --renderer text # force the colored Unicode renderer
coffee --help
```

Q, Escape, or Ctrl-C quits and releases the sleep hold. The temporary terminal
screen and input mode are restored on exit. No network requests are needed.

WezTerm automatically gets full-resolution inline PNG frames; other terminals
and multiplexers default to colored Unicode. `--renderer image` explicitly
selects the inline-image protocol. The animation follows terminal resizing.

`scene.images` contains the inline PNG frames; `scene.frames` contains the text
renderer's RGB frames. `scene.apng` is the reference animation. These assets
are included in Git, so a regular clone is enough; Git LFS is not required.

To uninstall the command, remove the `coffee` symlink from `~/.local/bin`.
Earlier local Swift/app experiments are excluded from the published repo.
