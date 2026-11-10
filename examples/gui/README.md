# Graphical score

COBOL manages the score. A C helper displays the choices in an X11 window.

## Prerequisites

Install COBOL Debugger and the tools below. Use a graphical session with an
accessible X server. An Xorg session works directly. On Wayland, the example
needs XWayland and a working `DISPLAY`.

| Platform | Build and debug dependencies |
| --- | --- |
| Fedora 44 | `sudo dnf install gnucobol gcc gdb libX11-devel` |
| Mageia 10 (x86_64) | As root, run `urpmi gnucobol gcc gdb lib64x11-devel` |
| Linux Mint (X11) | `sudo apt install gnucobol build-essential gdb libx11-dev` |

On Mageia 10 Live, open the graphical desktop, connect to the network and
enable the Mageia 10 package repositories before running the Mageia command.
Copy the example to a writable folder. Save it and any build results to
persistent storage if you need them after rebooting a non-persistent session.

Before running the example, check that `cobc --version` and `gdb --version`
work and that `printf '%s\n' "$DISPLAY"` prints your display address.

## Build and debug

Open a terminal in this example folder and build:

```bash
mkdir -p bin
cd bin
cobc -free -x -g -fsource-location -ftraceall -O0 -save-temps \
  -o score ../score.cob ../score_window.c -lX11
cobol-debugger ./score --source ../score.cob
```

Set a breakpoint on `if selection`, then click **Run** and choose **Add one** in
the program window. Inspect `selection` and step until `score` becomes 6.
Continue to see the result in **Program output**.

You can also open this folder in OpenCobolIDE and build it with debug enabled.
The IDE detects the C helper and its X11 library.
