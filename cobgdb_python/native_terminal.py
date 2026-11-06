"""Give a Linux inferior its own desktop terminal without reading its input."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import time


def open_terminal(cwd):
    """Return the terminal's TTY and a lifetime handle, or raise OSError."""
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        raise OSError('No desktop display is available')
    for name, option in [('gnome-terminal', ['--wait', '--title=COBGDB program terminal', '--']),
                         ('konsole', ['--nofork', '-e']),
                         ('xfce4-terminal', ['--disable-server', '-x']),
                         ('xterm', ['-e']), ('x-terminal-emulator', ['-e'])]:
        terminal = shutil.which(name)
        if terminal:
            break
    else:
        raise OSError('No supported desktop terminal was found')

    lifetime = tempfile.TemporaryDirectory(prefix='cobgdb-terminal-')
    ready = Path(lifetime.name)/'tty'
    helper = [
        'sh', '-c',
        'device=$(tty) || exit 1; printf "%s\\n" "$device" > "$1.tmp"; '
        'mv "$1.tmp" "$1"; printf "COBGDB program terminal\\n"; '
        'while test -e "$1" && kill -0 "$2" 2>/dev/null; do sleep 1; done',
        'cobgdb-terminal', str(ready), str(os.getpid()),
    ]
    if name == 'x-terminal-emulator' and Path(terminal).resolve().name == 'gnome-terminal.wrapper':
        helper = [shlex.join(helper)]
    try:
        process = subprocess.Popen([terminal, *option, *helper], cwd=cwd,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if ready.is_file():
                tty = ready.read_text().strip()
                if tty.startswith('/dev/') and Path(tty).is_char_device():
                    return tty, (lifetime, process)
                break
            if process.poll() not in (None, 0):
                break
            time.sleep(0.05)
        raise OSError('The desktop terminal did not provide a usable TTY')
    except BaseException:
        lifetime.cleanup()
        if 'process' in locals() and process.poll() is None:
            process.terminate()
        raise
