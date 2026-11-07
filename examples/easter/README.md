# Easter: input, calculations, and reports

This program calculates Eastern Church moveable feasts for a supplied year and
writes an `MV_FEASTSyyyy.TXT` report. Use it to learn program input, grouped fields,
conditional branches, breakpoints, and variable changes. No database is required.

From the repository root on Linux:

```bash
mkdir -p examples/easter/build
cd examples/easter/build
cobc -x -g -fsource-location -ftraceall -O0 -save-temps \
  -o easter ../easter.cbl
```

On Windows, use `easter.exe` as the output name and the corresponding paths.
Read output in Program output and use the input box or Send input on Linux.

Start the GUI from the repository root:

```bash
python3 -m cobgdb_python.frontend
```

1. Select `examples/easter/build/easter` with **Executable**.
2. Its COBOL source opens automatically. Add breakpoints at lines **79** (ACCEPT)
   and **82** (the statement after input).
3. Click **Run**. At line 79, click **Continue**, then enter `2031` in the debugger input box and click **Send input**.
4. At the next pause, inspect ETOS in the popup. It should show `2031`.
5. Continue or step through calculations and watch the fields change.
6. Remove unneeded breakpoints and Continue to exit. Read the output and find
   the report in `examples/easter/build/`, the executable's working directory.

The legacy source encoding is handled by the viewer's fallback. Compile with
debug can rebuild this single-source example after its initial executable load.
The flowchart supports its explicit IF branches; blue marks observed debugger
pauses, not every line traversed between Continue stops.

Existing reports from the old `examples/build/` folder are preserved here under
`build/`. They are generated artifacts and excluded from Git.
