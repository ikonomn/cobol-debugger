# Hello: first debugging steps

A tiny COBOL program adds 1 to COUNTER and displays the result. No database or
program input is required.

From the repository root on Linux:

```bash
mkdir -p examples/hello/build
cd examples/hello/build
cobc -x -g -fsource-location -ftraceall -O0 -save-temps \
  -o hello ../hello.cob
```

On Windows, use `hello.exe` as the output name and the corresponding paths.
Start the debugger from the repository root:

```bash
python3 -m cobgdb_python.frontend
```

1. Select `examples/hello/build/hello` with **Executable**.
2. `hello.cob` should open automatically. Check the breakpoint box on line **7**.
3. Click **Run**. The program pauses before ADD; COUNTER is `1`.
4. Click **Next COBOL line**. It reaches DISPLAY; COUNTER becomes `2`.
5. Click **Continue**. Program output contains `Counter: 2`, followed by normal exit.

The variables popup refreshes at each pause. Reopen it with **Variables**.
**Flowchart** displays the simple source flow. After the initial load, the GUI's
Compile with debug button can rebuild this example in the same `build/` folder.
