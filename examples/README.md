# Debugger examples

Choose an example according to what you want to learn. These are separate projects;
their source, generated files, and instructions stay together.

| Example | Start here for | Additional requirements | Main source |
| --- | --- | --- | --- |
| [Hello](hello/README.md) | First breakpoint, Next COBOL line, variable changes | GnuCOBOL + GDB | `hello/hello.cob` |
| [Easter](easter/README.md) | Input, calculations, grouped fields, report file | GnuCOBOL + GDB | `easter/easter.cbl` |
| [Graphical score](gui/README.md) | Native window choices, COBOL breakpoints and variable inspection | GnuCOBOL + GDB + C compiler, with X11 development files on Linux or MinGW on Windows | `gui/score.cob` |
| [World Cities](worldcities/README.md) | SQL cursor, row-by-row values, COPY members, larger program | GixSQL and SQLite driver, plus GnuCOBOL + GDB | `worldcities/src/select-greek-cities.cbl` |

**Suggested order**  Hello → Easter → Graphical score → World Cities.

Use the per-example instructions to create an initial debug executable, then
select it with **Executable**. The matching source opens automatically when
available. Hello and Easter can then be recompiled with **Compile with debug**;
Graphical score uses the build commands in its guide to link the native C window bridge.
World Cities uses its supplied build script for GixSQL preprocessing and linkage.

**All compiled COBOL programs and modules need `-g -fsource-location -ftraceall
-O0 -save-temps` for the supported debugging experience.** Keep generated C and
header files and rebuild after moving source folders.

Generated binaries and reports belong in the example's own `build/` directory
(World Cities additionally uses `bin/`). They are ignored by Git. The full,
unchanged World Cities dataset is retained in `worldcities/data/`.

## Previous locations

- `examples/hello.cob` → `examples/hello/hello.cob`
- `examples/easter.cbl` → `examples/easter/easter.cbl`
- `examples/build/` (Easter builds/reports) → `examples/easter/build/`

Historical binaries elsewhere in the repository may still refer to the old paths.
Use the new builds described in each example's README.
