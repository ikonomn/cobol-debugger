# COBGDB 0.1.0 release notes

- The desktop GUI opens a native terminal for program input and output on Linux, with embedded fallback when the terminal cannot be opened. Windows requests a separate inferior console from GDB.
- The new graphical COBOL score example uses an X11 window on Linux and a Win32 dialog on Windows. Its COBOL branch and variables can be inspected while debugging.
- The launcher supports manual selection, an executable argument and an optional original-source argument. It reads portable project settings and retains separate debugger and compiler workers.
- The independent debugger includes COBOL breakpoints, stepping, source mapping, variable inspection, flowcharts, PDF export and session logs.

| Target | Planned deliverables | Status |
| --- | --- | --- |
| Fedora 44 | 0.1.0-2.fc44 binary and source RPMs | Native build and desktop verification pending |
| Mageia 10 | 0.1.0-2.mga10 binary and source RPMs | Native build and desktop verification pending |
| Windows 11 x64 | cobgdb-python-gui.exe and Inno Setup installer | Native build and installer verification pending |

The graphical example was exercised locally on Linux with GDB, a native terminal, a window click, a COBOL breakpoint, variable inspection and stepping to normal exit. See [the graphical example](examples/gui/README.md) and [Windows build instructions](packaging/windows/README.md).
