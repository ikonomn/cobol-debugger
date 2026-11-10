# COBOL Debugger 0.1.0 release notes

- The Help menu opens offline instructions and an About dialog. Its Examples button opens the full installed collection, including the index and required data files. Linux and Windows launchers use the COBOL Debugger icon.

- Restored the original embedded Program output pane and Linux input box. The GUI launches programs through the managed PTY.
- The new graphical COBOL score example uses an X11 window on Linux and a Win32 dialog on Windows. Its COBOL branch and variables can be inspected while debugging.
- The launcher supports manual selection, an executable argument and an optional original-source argument. It reads portable project settings and retains separate debugger and compiler workers.
- The independent debugger includes COBOL breakpoints, stepping, source mapping, variable inspection, flowcharts, PDF export and session logs.

| Target | Planned deliverables | Status |
| --- | --- | --- |
| Fedora 44 | 0.1.0-5.fc44 binary and source RPMs | Native build and desktop verification pending |
| Mageia 10 | 0.1.0-5.mga10 binary and source RPMs | Native build and desktop verification pending |
| Windows 11 x64 | cobol-debugger.exe and Inno Setup installer | Native build and installer verification pending |

The graphical example was exercised locally on Linux with GDB, a native terminal, a window click, a COBOL breakpoint, variable inspection and stepping to normal exit. See [the graphical example](examples/gui/README.md) and [Windows build instructions](packaging/windows/README.md).


## Release files

Keep the exact committed build source in the dedicated `cobgdb-python-0.1.0.tar.gz` archive, following the modern11.6 release layout. Record its commit ID and checksum alongside the release files.

Build and verify Windows 11 separately. Its release downloads are the standalone executable and Inno Setup installer. Use the source archive for the Windows build instructions and recipes. Keep the Fedora and Mageia transfer kits and native build logs with the internal build records.
