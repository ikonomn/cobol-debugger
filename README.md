# COBOL Debugger

A graphical GnuCOBOL debugger built with Python and powered by GDB. Set
breakpoints, step through COBOL statements, inspect variables, and interact
with programs through the debugger's input and output panes.

## Install and open

Install the Debian package on Debian, Ubuntu, or Linux Mint. From the folder
containing the package:

```bash
sudo apt install ./cobol-debugger_0.1.0-13_all.deb
```

Open **COBOL Debugger** from the applications menu or run `cobol-debugger`.
Install GnuCOBOL if you also need to build the examples.

For a source checkout, install Python 3.10+, GDB, and the GUI dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e '.[gui]'
cobol-debugger
```

## Build a program for debugging

In OpenCobolIDE, enable **Compile with debug** in Project Compiler Settings or
**Compile this file with debug** in File Compiler Settings, then rebuild.

With your own build tool, compile the executable and any callable COBOL
modules with these flags:

```text
-g -fsource-location -ftraceall -O0 -save-temps
```

Keep the generated C and header files from the same build. OpenCobolIDE
project builds retain them in `debug_data/`. Rebuild after moving the source
or project so the recorded paths match.

## Debug the executable

1. Click **Executable** and select the program. Click **Source** if the
   debugger cannot find the original COBOL source.
2. Set a breakpoint in the source margin and click **Run**.
3. At the stop, inspect values with **Variables**. Use **Next COBOL line** to
   step, **Step into external CALL** to enter a callable COBOL module, or
   **Continue** to resume.
4. Read DISPLAY output in **Program output**. To supply an ACCEPT value, let
   the program run to the input, type the value and click **Send input**.

You can also open an executable and its source directly:

```bash
cobol-debugger /path/to/program --source /path/to/program.cob
```

**Flowchart** shows the source flow and observed stops. **Open log** opens the
session log when a debug session is loaded.

## Runtime folders

For a project, COBOL Debugger reads the accepted runtime settings in
`config/project.json`. The default working directory is `bin/`. Change the
working directory in OpenCobolIDE's **Review Project Folders** dialog when
the program expects files relative to another directory.

**Data search folders** supplies GnuCOBOL's `COB_FILE_PATH`. Enter one folder per
line, such as `data`. A folder inside the project can be saved as a path relative
to the project root. Save the settings to apply them.

Use a single data folder for reliable file lookup with the tested GnuCOBOL
runtime. The IDE can save several entries and joins them using the system path
separator, but the runtime may treat the resulting value as one directory.
For a program that uses a specific relative path or a database connection
file, set the working directory that the program expects.

## Examples

Choose **Help → About COBOL Debugger → Examples** to open the writable example
folders. Each guide gives the build command and a short debugging exercise.

- [Hello](examples/hello/README.md) for a first breakpoint and variable change.
- [Easter](examples/easter/README.md) for terminal input and a generated report.
- [Countries](examples/countries/README.md) for reading a bundled data file.
- [Graphical score](examples/gui/README.md) for a COBOL program with a C/X11 helper.
- [EU Cities](examples/eu-cities/README.md) for GixSQL, SQLite, and cursor stepping.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Breakpoint stays pending or source is missing | Rebuild with the debug flags and keep the matching source, C and headers. |
| Variables are unavailable | Pause in user code and verify the generated files belong to that executable. |
| Program waits for input | Continue from the ACCEPT breakpoint, then use **Send input**. |
| Program cannot find a data or configuration file | Check the saved working directory and the program's relative paths. |
| EU Cities opens a different database | Clear an inherited `DB_CONFIG_FILE` and run from the example's `bin/`. |

For details on the backend and development workflow, see [Development](DEVELOPMENT.md).

## License

The original COBOL Debugger software is available under the
[Zero-Clause BSD license](LICENSE). This grant covers the original debugger
software. Dependencies and material obtained from other projects retain their
own terms. The bundled example data comes from GeoNames under CC BY 4.0. See the
[example data sources](examples/DATA-SOURCES.md) for attribution and changes.
Other imported example material still needs review before public packaging.
