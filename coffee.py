#!/usr/bin/env python3
"""The coffee-cat scene, rendered in the current terminal. No GUI or runtime packages."""
import argparse
import base64
import fcntl
import json
import math
import os
from pathlib import Path
import select
import shutil
import signal
import struct
import subprocess
import sys
import termios
import time
import tty
import zlib

ROOT = Path(__file__).resolve().parent
GROUND = (9, 12, 24)
BITS = ((0, 3), (1, 4), (2, 5), (6, 7))
# Fixed ordered stippling: shading stays planted while the steam drifts.
THRESHOLDS = ((0.12, 0.62), (0.87, 0.37), (0.56, 0.06), (0.31, 0.81))

def use_inline_image(renderer):
    if renderer != 'auto':
        return renderer == 'image'
    # Send static PNG frames ourselves: WezTerm pauses native APNGs without focus.
    # Multiplexer passthrough is deliberately left to an explicit --renderer image.
    return not os.environ.get('TMUX') and (
        os.environ.get('TERM_PROGRAM', '').lower() == 'wezterm'
        or bool(os.environ.get('WEZTERM_PANE')))

def image_geometry(size):
    columns, lines = max(1, size.columns - 1), max(1, size.lines - 1)
    cell_width, cell_height = 1.0, 2.0
    try:
        rows, cols, xpixels, ypixels = struct.unpack('HHHH', fcntl.ioctl(
            sys.stdout.fileno(), termios.TIOCGWINSZ, b'\0' * 8))
        if rows and cols and xpixels and ypixels:
            cell_width, cell_height = xpixels / cols, ypixels / rows
    except OSError:
        pass
    width = max(1, min(columns - 2, int(max(1, lines - 3) * cell_height * 2 / cell_width)))
    height = max(1, min(max(1, lines - 2), math.ceil(width * cell_width / (2 * cell_height))))
    return width, height, max(0, (columns - width) // 2), max(0, (lines - height - 1) // 2)

def show_inline_image(payload, size):
    width, height, x, y = image_geometry(size)
    # Batch the clear and replacement so frames do not flash between images.
    sys.stdout.write(f'\x1b[?2026h\x1b[2J\x1b[{y + 1};{x + 1}H'
        f'\x1b]1337;File=inline=1;width={width};height={height};'
        'preserveAspectRatio=1;doNotMoveCursor=1:' + payload + '\a')
    hint = 'Q / Esc / Ctrl-C to quit'
    if size.lines > height + 2:
        sys.stdout.write(f'\x1b[{y + height + 2};{max(1, (size.columns - len(hint)) // 2)}H'
            '\x1b[38;2;165;172;216m' + hint[:max(1, size.columns - 1)])
    sys.stdout.write('\x1b[?2026l')
    sys.stdout.flush()

def load_image_frames():
    header, packed = (ROOT / 'scene.images').read_bytes().split(b'\n', 1)
    meta = json.loads(header)
    frames = []
    offset = 0
    for _ in range(meta['count']):
        if offset + 4 > len(packed):
            raise ValueError('truncated image frame header')
        length = struct.unpack_from('>I', packed, offset)[0]
        offset += 4
        image = packed[offset:offset + length]
        if len(image) != length or not image.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('invalid image frame')
        frames.append(base64.b64encode(image).decode('ascii'))
        offset += length
    if offset != len(packed) or not frames or meta['fps'] <= 0:
        raise ValueError('invalid image frame pack')
    return meta, frames

def quit_requested(input_fd):
    data = os.read(input_fd, 1024)
    # Focus reports, if enabled by the shell, are not an Escape keypress.
    data = data.replace(b'\x1b[I', b'').replace(b'\x1b[O', b'')
    return data in (b'q', b'Q', b'\x1b')

def load_scene():
    header, compressed = (ROOT / 'scene.frames').read_bytes().split(b'\n', 1)
    meta = json.loads(header)
    pixels = zlib.decompress(compressed)
    stride = meta['width'] * meta['height'] * 3
    if len(pixels) != stride * meta['count']:
        raise ValueError('invalid scene frame size')
    return meta, pixels, stride

def geometry(columns, lines):
    width = max(1, min(100, columns - 2, max(1, lines - 4) * 4))
    height = max(1, round(width / 4))
    return width, height, max(0, (columns-width)//2), max(0, (lines-height-2)//2)

def raster(frame, source_width, source_height, width, height):
    cells=[]
    for row in range(height):
        for col in range(width):
            mask=0; red=green=blue=weight=0
            for dy in range(4):
                sy=min(source_height-1, int((row*4+dy+0.5)*source_height/(height*4)))
                for dx in range(2):
                    sx=min(source_width-1, int((col*2+dx+0.5)*source_width/(width*2)))
                    offset=(sy*source_width+sx)*3
                    r,g,b=frame[offset:offset+3]
                    lum=(r*0.299+g*0.587+b*0.114)/255
                    # Keep the dark room quiet; light on fur and ceramic carries the dots.
                    density=max(0, min(1, (lum-0.045)*1.65))
                    if density > THRESHOLDS[dy][dx]:
                        mask |= 1 << BITS[dy][dx]
                        red+=r;green+=g;blue+=b;weight+=1
            if mask:
                cells.append((chr(0x2800+mask), red//weight, green//weight, blue//weight))
            else:
                cells.append((' ', *GROUND))
    return cells

def main():
    parser=argparse.ArgumentParser(prog="coffee", description=__doc__,epilog='Default: -s (system sleep hold, AC power only). Q, Escape, or Ctrl-C quits.')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('-s',dest='assertion',action='store_const',const='-s',help='prevent system sleep (default; AC only)')
    mode.add_argument('-d',dest='assertion',action='store_const',const='-d',help='prevent display sleep')
    mode.add_argument('-sd','-ds',dest='assertion',action='store_const',const='-ds',help='prevent both display and system sleep')
    parser.set_defaults(assertion='-s')
    parser.add_argument('-t','--duration',type=float,help='quit after this many seconds')
    parser.add_argument('--renderer', choices=('auto', 'image', 'text'), default='auto',
        help='auto: focus-independent image frames in WezTerm, colored text elsewhere')
    parser.add_argument('--windowed',action='store_true',help=argparse.SUPPRESS) # Old spelling; terminal is always used.
    args=parser.parse_args()
    if args.duration is not None and (not math.isfinite(args.duration) or args.duration <= 0):
        parser.error('duration must be a positive number')
    if not sys.stdout.isatty():
        parser.error('run coffee in a terminal')
    image_mode = use_inline_image(args.renderer)
    try:
        if image_mode:
            meta, image_frames = load_image_frames()
        else:
            meta,pixels,stride=load_scene()
    except (OSError,ValueError,zlib.error) as error:
        parser.error(str(error))
    old_handlers={}
    hold=None; old_terminal=None; entered=False
    input_fd=sys.stdin.fileno() if sys.stdin.isatty() else None
    stopped=False
    def stop(signum, frame):
        nonlocal stopped
        stopped=True
    try:
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            old_handlers[sig]=signal.signal(sig,stop)
        hold=subprocess.Popen(['/usr/bin/caffeinate',args.assertion,'-w',str(os.getpid())])
        if input_fd is not None:
            old_terminal=termios.tcgetattr(input_fd);tty.setcbreak(input_fd)
        # Alternate buffer preserves the caller's scrollback and prompt, never window geometry.
        sys.stdout.write('\x1b[?1049h\x1b[?25l\x1b[48;2;9;12;24m\x1b[2J')
        sys.stdout.flush();entered=True
        start=time.monotonic();interval=1/meta['fps'];previous=None;old_size=None;cache={};old_frame=None
        while not stopped:
            elapsed=time.monotonic()-start
            if args.duration is not None and elapsed>=args.duration:break
            if hold.poll() is not None:raise RuntimeError('caffeinate exited unexpectedly')
            size=shutil.get_terminal_size()
            if image_mode:
                frame_index = int(elapsed * meta['fps']) % meta['count']
                if size != old_size or frame_index != old_frame:
                    show_inline_image(image_frames[frame_index], size)
                    old_size = size
                    old_frame = frame_index
                now = time.monotonic() - start
                wait = max(0, interval - now % interval)
                if args.duration is not None:
                    wait = max(0, min(wait, args.duration - now))
                if input_fd is not None:
                    ready, _, _ = select.select([input_fd], [], [], wait)
                    if ready and quit_requested(input_fd):
                        break
                else:
                    time.sleep(wait)
                continue
            columns=max(1,size.columns-1);lines=max(1,size.lines-1)
            width,height,x,y=geometry(columns,lines)
            if size!=old_size:
                cache.clear();previous=None;sys.stdout.write('\x1b[2J');old_size=size
            frame_index=int(elapsed*meta['fps'])%meta['count']
            if frame_index not in cache:
                frame=memoryview(pixels)[frame_index*stride:(frame_index+1)*stride]
                cache[frame_index]=raster(frame,meta['width'],meta['height'],width,height)
            cells=cache[frame_index]
            output=[];last_colour=None;last_position=None
            for n,cell in enumerate(cells):
                if previous is not None and cell==previous[n]:continue
                row,col=divmod(n,width)
                if last_position!=(row,col):output.append(f'\x1b[{y+row+1};{x+col+1}H')
                ch,r,g,b=cell
                if last_colour!=(r,g,b):output.append(f'\x1b[38;2;{r};{g};{b}m');last_colour=(r,g,b)
                output.append(ch);last_position=(row,col+1)
            if previous is None:
                caption='must... stay... awake...'
                if lines>=height+2:
                    output.append(f'\x1b[{y+height+2};{max(1,(columns-len(caption))//2+1)}H\x1b[38;2;165;172;216m'+caption[:columns])
            sys.stdout.write(''.join(output));sys.stdout.flush();previous=cells
            now=time.monotonic()-start
            wait=max(0,interval-now%interval)
            if args.duration is not None:wait=max(0,min(wait,args.duration-now))
            if input_fd is not None:
                ready,_,_=select.select([input_fd],[],[],wait)
                if ready and quit_requested(input_fd):break
            else:time.sleep(wait)
    finally:
        if old_terminal is not None:termios.tcsetattr(input_fd,termios.TCSADRAIN,old_terminal)
        if entered:
            sys.stdout.write('\x1b[?2026l\x1b[0m\x1b[?25h\x1b[?1049l');sys.stdout.flush()
        if hold is not None and hold.poll() is None:
            hold.terminate()
            try:hold.wait(timeout=2)
            except subprocess.TimeoutExpired:hold.kill();hold.wait()
        for sig,handler in old_handlers.items():signal.signal(sig,handler)

if __name__=='__main__':
    try:main()
    except (RuntimeError,OSError) as error:
        print('coffee: '+str(error),file=sys.stderr);sys.exit(1)
