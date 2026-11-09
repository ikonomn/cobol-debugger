# Graphical score

COBOL manages the score. A C helper displays the choices in an X11 window.
Install a C compiler and the X11 development headers and libraries.

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
