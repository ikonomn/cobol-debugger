# Debug a graphical COBOL program

This example keeps its score and decision in COBOL. A small C bridge displays an X11 window on Linux or a Win32 dialog on Windows.

Build from this directory using GnuCOBOL and the matching C compiler. Linux requires X11 headers and libraries.

```bash
mkdir -p build
cd build
cobc -free -x -g -fsource-location -ftraceall -O0 -save-temps -o gui-score ../score.cob ../score_window.c -lX11
```

On Windows with a MinGW GnuCOBOL toolchain, run from a PowerShell prompt.

```powershell
New-Item -ItemType Directory -Force build
Set-Location build
cobc -free -x -g -fsource-location -ftraceall -O0 -save-temps -o gui-score.exe ../score.cob ../score_window.c -luser32
```

Launch `cobgdb-python-gui` with the built executable and `--source` pointing to `score.cob`. Set a breakpoint on line 9, the `if selection` statement after the window returns. Click Run, choose **Add one** in the program window, inspect `selection` at the breakpoint, and step to observe `score` become 6. Continue and read `SCORE` in the program terminal. Repeat with **Subtract one** to exercise the other branch. Keep the generated C and headers in the build folder with the executable.
