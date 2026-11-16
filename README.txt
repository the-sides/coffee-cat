COFFEE

coffee                 Animate the selected coffee-cat scene in the current terminal.
coffee -d              Prevent display sleep instead of the default system hold.
coffee -sd             Prevent both display and system sleep.
coffee -t 3600         Quit after one hour.
coffee --help          Full usage.

Default: caffeinate -s (system sleep hold; AC power only).
Q, Escape, Ctrl-C, SIGTERM or SIGHUP exits and releases the hold.
The existing window is used as-is: no GUI, browser, activation, resizing,
full-screen switch, terminal preference changes or runtime network requests.
The temporary terminal screen is restored on exit, including its cursor and input mode.
The scene fits the current rows/columns and follows user resizing.

Rendering: WezTerm is detected automatically and receives full-resolution
static PNG frames through its native OSC 1337 image protocol. Coffee advances
them from its own monotonic clock, independent of terminal focus. It does not
rely on WezTerm's native animated-image player (which pauses without focus).
Lettering, colors, and dot shapes are preserved. 1000x500, 120 frames, 6 fps,
20-second loop. Synchronized rendering batches each clear/replacement to avoid
flashing between frames. Resize re-fits the scene within the existing pane.
Focus-in/out reports are ignored rather than interpreted as the Escape key.
Other terminals retain the colored Unicode fallback. Multiplexers default to text.

coffee --renderer image   Explicitly use the inline-image protocol.
coffee --renderer text    Explicitly use the colored Unicode fallback.

There are no runtime dependencies beyond the locally installed Python standard library.

Launcher: ~/.local/bin/coffee
Player: coffee.py
Image frame pack: scene.images
Reference animation (unused by the player): scene.apng
Fallback frames: scene.frames

The earlier Coffee.app and its Swift source are retained locally under legacy/ (not published).
The coffee command never starts that app.

Verified using a pseudo-terminal: playback; default -s child assertion; timed,
Q and Ctrl-C exits; resize handling; exact terminal-mode restoration; cursor
and screen restoration; no window manipulation sequences; no orphaned caffeinate.

2026-11-16 validation: PNG CRCs and APNG sequence/rectangle checks; exact 20s
loop; browser decode and playback; pseudo-terminal auto-detection; byte-exact
inline payload; resize; Q, SIGINT, timed exits; terminal settings, cursor and
screen restoration; no window manipulation; -s hold and child cleanup. Live
WezTerm visual inspection was blocked by computer-use permissions, so the native
in-app appearance was not visually checked by the agent.

Protocol references:
https://wezterm.org/imgcat.html
https://wezterm.org/changelog.html (20210314 native animated GIF/PNG support)
https://iterm2.com/documentation-images.html

2026-11-16 background-playback update: all 120 PNGs are static, full resolution,
and form the 20-second loop. Pseudo-terminal tests injected focus-out and
verified subsequent distinct frames kept arriving. Quit, SIGINT, resize,
text fallback, default -s and child/terminal cleanup passed. Live visual
inspection of WezTerm remains unavailable under computer-use permissions.
