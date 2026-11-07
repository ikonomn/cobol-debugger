# cobgdb-python

A simple standalone GnuCOBOL debugger: follow COBOL execution, set breakpoints,
send program input, and watch variable values change. The PyQt5 interface
communicates with an independent Python backend through JSON and GDB/MI2.
No COBGDB code, library, or executable is required.

The internal project compiler reads portable `config/project.json` files,
including projects created by OpenCobolIDE. **OpenCobolIDE is not required.**
Project configuration and IDE preferences are never rewritten.

## Reading this guide

This README and the example guides are Markdown (`.md`) files. To view them with
formatted headings, tables and links in a web browser, install a **Markdown viewer
browser extension**. For local files, enable the extension's local-file access
permission if your browser requires it, then open the `.md` file.

The extension is optional: Markdown-capable editors and repository websites can
also render the guide, and any text editor can read its plain-text contents.

## Contents

1. [Install and start](#install-and-start)
2. [Prepare a debug build](#prepare-a-debug-build)
3. [First debugging session](#first-debugging-session)
4. [Window and controls](#window-and-controls)
5. [Breakpoints and execution](#breakpoints-and-execution)
6. [Variables and program input](#variables-and-program-input)
7. [Compile programs](#compile-programs) and [runtime folders](#runtime-working-directory-and-data-search-folders)
8. [GixSQL programs](#gixsql-programs)
9. [Flowcharts and PDF export](#flowcharts-and-pdf-export)
10. [Session logs](#session-logs)
11. [Examples](#examples)
12. [Troubleshooting](#troubleshooting)
13. [Platform support and limitations](#platform-support-and-limitations)
14. [Backend protocol and development](#backend-protocol-and-development)

## Install and start

### Requirements

- Python 3.10 or newer; PyQt5 5.15.x for the GUI.
- GDB on PATH, compatible with the program's target architecture.
- GnuCOBOL (`cobc`) on PATH for compilation.
- Permission for GDB to trace its child process.
- For SQL programs: GixSQL preprocessor/runtime, SQLCA copybook and database driver.

The backend itself uses only Python's standard library.

### Debian / Ubuntu / Linux Mint package

Build a local package from the source folder:

```bash
python3 scripts/make_deb.py
sudo apt install ./dist/cobgdb-python_0.1.0-1_all.deb
```

Start **COBGDB Python Debugger** from the applications menu, or run
`cobgdb-python-gui`. The backend command is `cobgdb-python`. No pip install or
OpenCobolIDE installation is required. GixSQL is installed separately if needed.
Examples and datasets stay in the source repository; use a writable project
folder when compiling. The package includes the Python modules, launchers,
desktop entry and documentation, with no session logs or compiled programs.
Installed-app logs use `~/.local/state/cobgdb-python/logs/`, or
`$XDG_STATE_HOME/cobgdb-python/logs/` when configured. Source checkouts retain
`logs/` in the repository. Uninstall with `sudo apt remove cobgdb-python`.

### Linux source installation

Install Python, pip, venv, GDB and GnuCOBOL with your distribution's package
manager. From the repository:

```bash
cd ~/cobgdb-python
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[gui]"
python -m cobgdb_python.frontend
```

For later sessions, activate that environment and run the same frontend command.
If installed in the system/user Python environment instead, start with:

```bash
cd ~/cobgdb-python
python3 -m cobgdb_python.frontend
```

Restart the GUI after updating its Python files. Editable installation requires
setuptools 64 or newer, as specified in `pyproject.toml`.

### Windows

Install a matching GnuCOBOL/MinGW toolchain and GDB. Put the tools and required
runtime DLL directories on PATH. In PowerShell, from the repository:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[gui]"
.\.venv\Scripts\python.exe -m cobgdb_python.frontend
```

Windows GDB console validation is pending.
See [platform support](#platform-support-and-limitations).

## Prepare a debug build

**CRUCIAL: Use `-g -fsource-location -ftraceall -O0 -save-temps` for ALL compiled
COBOL programs and separately compiled modules. Perform a full project rebuild
after changing these settings, and retain the generated C/header files.**

| Option | Purpose |
| --- | --- |
| `-g` | Enables C compiler debug information for GDB inspection. |
| `-fsource-location` | Generates COBOL source-location information. |
| `-ftraceall` | Generates section/paragraph/statement trace code; also enables source locations. |
| `-O0` | Disables optimization for more predictable stepping and variable inspection. |
| `-save-temps` | Retains generated files used for COBOL line mapping and field metadata. |

`-debug` enables runtime checks; it is distinct from `-g`. Existing runtime-check
flags can be kept alongside these debugging options. Copybooks inherit options
from the program that includes them; do not compile them separately. For GixSQL,
pass these options to `cobc` when compiling the generated `.cbsql`.

### OpenCobolIDE project compiler settings on Linux

**With OpenCobolIDE modern12, enable Debug compilation in Configure Project →
Runtime folders / debug, then Save and Rebuild Project.** The IDE adds the required
`-g -fsource-location -ftraceall -O0 -save-temps` flags and retains matching C/header
files in `debug_data/`. The project compiler settings below remain useful for
other compiler options and earlier IDE builds.

**CRUCIAL: Configure the current Linux project through the Project compiler
settings dialog. Check “Use these project settings”, leave “Use IDE default
compiler flags” unchecked, and enter the debug options explicitly in “Extra
compiler flags”. Do this for each project you intend to debug.**

For example, retaining warnings and runtime checks alongside debugger options:

```text
-Wall -debug -g -fsource-location -ftraceall -O0 -save-temps
```

Keep the compiler, GixSQL tools, copybook/library paths, source format and listing
fields appropriate to that project. In the shown World Cities layout, Copybook
paths is explicitly `copybooks`, and Listing filename is `build/{stem}.lst`.
A blank Compiler path can use the installed compiler. Do not replace existing
required tool/library settings with generic example values.

Check any separate source-specific settings so every compiled program/module
retains the debug options, then rebuild the whole project. Copybooks use their
including program's compilation options.

**The legacy Preferences → Compiler interface is not the recommended Linux setup
for this guide. Its cleanup belongs to a future OpenCobolIDE build.** The
checkbox mentioning IDE default flags exists in the dialog, but this guide does
not require selecting it or following an “IDE defaults → project defaults →
source overrides” sequence. Configure and verify the project dialog directly.
This debugger reads saved settings without changing them.

## First debugging session

Start with [Hello](examples/hello/README.md). Create its initial executable from
the repository root on Linux:

```bash
mkdir -p examples/hello/build
cd examples/hello/build
cobc -x -g -fsource-location -ftraceall -O0 -save-temps \
  -o hello ../hello.cob
```

On Windows, use the corresponding paths and `-o hello.exe`. Start the GUI from
the repository root, then:

1. Click **Executable** and select `examples/hello/build/hello`.
2. Its source should open automatically. Otherwise use **Source** to open
   `examples/hello/hello.cob`.
3. Check the box beside line **7** and click **Run**.
4. At the pause, inspect COUNTER in the variables popup: its value is `1`.
5. Click **Next COBOL line**. COUNTER becomes `2` before DISPLAY executes.
6. Click **Continue**. Program output shows `Counter: 2`, then normal exit.

Only Executable is enabled at startup, so the first executable must already
exist. Later standalone rebuilds can use **Compile with debug**.

### Automatic source selection

The debugger asks GDB for recorded source paths and considers accessible `.cob`,
`.cbl` and `.cbsql` files. It prefers a unique filename matching the executable,
ignoring a trailing `-debug`. A unique matching `.cbsql` takes priority for GixSQL;
a single available COBOL source can also be selected automatically.

Missing or ambiguous sources leave **Source** available as a manual fallback.
Discovery uses debug metadata, not a recursive directory search. Copybooks open
as execution enters them. Rebuild after moving files so recorded paths match.

## Window and controls

The main window fits the available screen area, allowing for borders and the
taskbar. Toolbar buttons wrap onto multiple rows. Source text is read-only and
uses a monospace font, syntax colors, and aligned headings:

**Breakpoint | Line number | COBOL source line**

The source filename, log filename and **Open log file** button share the row
above the source pane. Hover over the log filename for its full path. The bottom
status bar shows whether execution is running, paused or exited.

| Control | Action |
| --- | --- |
| **Executable** | Loads a compiled program and attempts to open its source. Select a binary, not a `.cbl` or `.cbsql`. |
| **Source** | Opens a source file manually; does not compile it. |
| **Compile with debug** | Calls the internal compiler using `config/project.json` for projects; uses a standalone debug build for other sources. |
| **Flowchart** | Opens a source-derived chart, with pause highlighting and PDF export. |
| **Run** | Starts the program, or restarts after exit. |
| **Continue** | Resumes until another stop or exit. |
| **Next COBOL line** | Advances over a COBOL operation, suppressing intermediate generated setup. |
| **Step into external CALL** | Tries to enter another COBOL program with available debug entry metadata. |
| **Finish** | Runs until the current GDB function returns, subject to breakpoints and signals. |
| **Pause** | Requests an interrupt while running. |
| **Variables** | Opens the variables popup and refreshes when paused. |
| **Stack** | Requests GDB stack frames, currently using generated/runtime function names. |
| **Send input** | Sends the input-box text plus Enter through the embedded Linux program terminal. |
| **Open log file** | Opens the current session log in the desktop's associated application. |

Controls follow execution state: source/build/run controls become available
after loading a session/source; stepping and inspection require a pause; Pause
requires a running program. Run is available before initial execution and after
exit. Conflicting actions are disabled while requests are pending.

| Output tab | Contents |
| --- | --- |
| **Debugger** | Commands, results, messages and errors. |
| **Program output** | Displays program output and echoed input. |
| **JSON events** | Complete backend messages for troubleshooting. |
| **Compiler** | Build diagnostics and success/failure messages. |

## Breakpoints and execution

### Mouse controls

Single-click a checkbox or line number to add/remove that line's breakpoint.
Double-clicking source text also works. A normal single click on source text
selects it. Checkboxes update after GDB acknowledges the request.

GDB may relocate a breakpoint on a non-executable line or leave it pending.
The checkbox currently tracks the requested line; the yellow execution highlight
shows the actual paused location. Inspect Debugger/JSON events for relocation.
The highlight clears while running and after exit; breakpoints remain.

### Next versus external CALL

**Next COBOL line** steps over calls. **Step into external CALL** can enter a
called COBOL program with available source/debug entry metadata. On ordinary
MOVE, ADD and DISPLAY statements the two actions often behave alike.

“External” means another COBOL program, not necessarily a separate shared library.
**Dedicated step-into behavior for internal PERFORM paragraphs/sections is not
implemented.** Next can nevertheless follow internal paragraphs as execution
moves through the generated function. Dynamically loaded programs without known
entry metadata may still need a manual breakpoint.

Generated statement markers and GDB line tables distinguish separate statements
sharing one source line. Backwards/repeated instruction addresses preserve new
loop visits. The highlight can therefore remain on one line while values change.
Recognized runtime helpers and generated initialization are skipped; unknown
stops are shown. Breakpoints, watchpoints, signals and Pause are preserved.
An internal limit of 256 operations pauses safely with a diagnostic.

### Finish and active breakpoints

**Finish respects active breakpoints.** If one is reached before the current
function returns, execution pauses and variables refresh. Another Finish starts
a new request; it does not ignore those breakpoints.

**Finish is not “finish this internal PERFORM.”** COBOL paragraphs can share one
generated C function. In the main program, finishing that function can run to
normal program exit; in a called program, it can return to the caller.

In the World Cities example, Finish stopped repeatedly at loop breakpoints.
After the remaining breakpoints were removed, Finish ran to normal exit. Use
Continue to run freely to the next stop, Next to follow operations, and Finish
when the intention is to leave the current function.

## Variables and program input

### Variables popup

The popup stays open without blocking the main window. It refreshes at every
pause after execution controls, including stops without a mapped COBOL line.

- Columns show COBOL name, value and format.
- Changed values are highlighted yellow relative to the previous snapshot.
- While running, values are dimmed and labelled as the previous pause's snapshot.
- After exit, the last paused values remain; they are not final live values.
- Fields without readable metadata show unavailable values or an empty table.

The backend reads program memory using generated field descriptors. It decodes
unsigned numeric DISPLAY fields, scale placement, text and group bytes. Other
formats are labelled as undecoded hexadecimal bytes. It does not call functions
inside the program to obtain values. Fields larger than 64 KiB are not read
automatically.

COPY members reuse metadata for the current program function. A first stop in a
copybook can locate its owning C file through unambiguous `#line` references.
Signed/packed/binary decoding, OCCURS expansion, name qualification, editing,
compiler-elided fields and comprehensive scope handling remain unfinished.

### ACCEPT and input

Read DISPLAY output in **Program output**. On Linux, enter values or menu choices in the debugger input box and press Enter or click **Send input**. At an ACCEPT breakpoint, Continue before entering the value. Windows embedded keyboard input remains pending.

For a breakpoint around input, see [Easter](examples/easter/README.md). Continue from the ACCEPT breakpoint before entering the value, then inspect ETOS at the next breakpoint. An explicitly supplied backend tty is also available.

## Compile programs

### Standalone sources

**Compile with debug** invokes `cobc` for one fixed-format source with the debug
options, retains generated C/headers, and places outputs in `build/` beside it.
For Easter this is `examples/easter/build/easter` (`.exe` on Windows).
Custom standalone flags, include paths and multi-source builds need a supplied
build script or an IDE project. Standalone `.cbsql`/copybooks are not compiled
with guessed options.

A rebuild stops the previous session and clears breakpoints. A successful
executable build loads into GDB but does not run; a failed build shows errors and
does not launch output. Reports normally go to the executable directory.

### OpenCobolIDE projects

A project is recognized by schema-version-1 **`config/project.json`**. Its layout:

```text
project/
├── src/        original COBOL programs
├── copybooks/  COPY members
├── bin/        executables and modules
├── build/      generated SQL and listings
├── debug_data/ retained generated C/headers in modern12 debug builds
├── data/       datasets
└── config/     project and runtime configuration
```

**Compile with debug** uses COBGDB's internal Python compiler worker. It reads
`config/project.json` on every build and calls `cobc` directly, without an IDE
installation, Qt build APIs, Bash, or an IDE/project build script. Invalid project
configuration is reported rather than falling back to guessed standalone flags.

The supported schema-1 settings are:

- Project `defaults` and source entries such as `sources["src/main.cbl"]`: flags,
  copybook paths, library paths/libraries, source format and listing settings.
- Compiler environment: `compiler_path`, tools `path`/`path_mode`, `cob_copy_dir`,
  `gixpp_path`, `gixsql_copy_dir`, and `gixsql_library_dir`.
- `debug.enabled`: adds **`-g -fsource-location -ftraceall -O0 -save-temps`** and
  retains generated `.c`/`.h` only in `debug_data/src/main/` for `src/main.cbl`.
- Accepted `runtime` working directory and `data_directories` (`COB_FILE_PATH`).

Source-specific values replace the corresponding project value; null values
inherit it. Disabling project defaults excludes them. Environment and listing
fields merge, and `source_format: "inherit"` retains the project format. These
are saved-file rules, not a sequence of selections in the IDE interface.

**IDE-global preferences are not read.** When a value is inherited from outside
this JSON, COBGDB uses its own defaults: `COBC` or `cobc` on PATH, no extra flags
or libraries, fixed source format unless directed otherwise, and a listing in
`build/`. Put essential options in the project JSON to reproduce a build across
applications. Paths in that JSON resolve against the project root. Compiler and
GixSQL tools can be command names on PATH or explicit executable paths. On
Windows, configure the matching compiler tools and runtime DLL directories in
PATH; native Windows verification is still pending.

The compiler detects `PROCEDURE DIVISION USING` as a callable module; other
sources become executables. Comments/literals are ignored and COPY members are
inspected. SQL programs are preprocessed by `gixpp`, with `.cbsql` kept in `build/`,
and linked with GixSQL. The compiler and preprocessor must be installed. Set
GixSQL paths explicitly where needed, especially on Windows. SQL stops may
still display generated `.cbsql` rather than original `.cbl` line numbers.
Build-control flags such as `-o`, `-x`, `-m`, or syntax-only modes are rejected
in extra flags because the builder owns output and compilation mode.

Executable programs and modules go to `bin/`; listings go to their configured
location, normally `build/`. Temporary debug compilation files are removed.
Only a successful build replaces the previous executable and its retained
C/headers. Keep the executable, COBOL source and generated metadata from the
same successful build together. If debug retention is disabled, saved debug
flags are preserved and missing required options produce a warning.

For example, this is a minimal portable configuration:

```json
{
  "schema_version": 1,
  "name": "example",
  "defaults": {
    "enabled": true,
    "flags": ["-Wall"],
    "copybook_paths": ["copybooks"],
    "listing": {"enabled": true, "filename": "build/{stem}.lst"}
  },
  "sources": {},
  "debug": {"enabled": true},
  "runtime": {
    "accepted": true,
    "working_directory": "bin",
    "data_directories": ["data"]
  }
}
```

Create the named folders before using accepted runtime settings. Without
accepted runtime settings, launch uses `bin/` and the current environment.
Missing accepted folders prevent launch. The debugger never scans or accepts
folder suggestions automatically; review them in the IDE or edit the JSON.

### Runtime working directory and data search folders

The original default working directory for project executables is **`bin/`**, in both OpenCobolIDE and the independent debugger. An explicitly saved project working directory overrides it. Changing data search folders does not change the working directory or move any files.

The IDE field **Data search folders (one per line)** supplies directories for GnuCOBOL runtime data-file access. For example:

```text
MyProject/
├── bin/customers
├── data/customers.dat
├── config/
└── src/
```

For a COBOL declaration containing a bare filename:

```cobol
SELECT CUSTOMER-FILE ASSIGN TO "customers.dat".
```

entering this directory in the field:

```text
data
```

sets the launched program's environment to the equivalent of:

```text
COB_FILE_PATH=/absolute/path/MyProject/data
```

The program still runs from `MyProject/bin/`. Relative entries in this field are resolved against the **project root**, so `data` means `MyProject/data`, not `MyProject/bin/data`. Project-relative settings remain portable when the project is moved.

#### Current limitation: use one directory

Although the field accepts one directory per line, the current implementation joins multiple entries with the platform path separator (`:` on Linux) into `COB_FILE_PATH`. **Do not currently use multiple entries with the tested GnuCOBOL 3.3-dev runtime.** A real file-open check succeeded with either single directory, but failed with status 35 when the two directories were joined with `:`. The current label therefore implies a multiple-directory search capability that is not working on this runtime.

Use a single existing directory, such as `data`, or leave the field empty. Multiple-directory handling still needs correction; accepting multiple lines in the interface is not proof that the runtime searches them. See the [GnuCOBOL runtime documentation](https://gnucobol.sourceforge.io/doc/gnucobol.html) for `COB_FILE_PATH`.

#### Entry and save rules

- Enter directories, not individual filenames. Absolute paths are also accepted.
- Do not add shell quotes around a path containing spaces. Use literal paths, not shell variables or `~` shortcuts.
- Blank lines are ignored; accepted directories must already exist.
- Review the suggestions before accepting them. The scanner does not create or relocate runtime files.
- In Preferences, enable **Use these runtime folders for this project**, then choose **OK**. The standalone Review Project Folders dialog saves with **Save**. Cancel discards that dialog's unaccepted edits.
- An empty directory list does not set or clear `COB_FILE_PATH`; an inherited value may remain active.

Settings are stored in the project's `config/project.json`, for example:

```json
"runtime": {
  "accepted": true,
  "working_directory": "bin",
  "data_directories": ["data"]
}
```

OpenCobolIDE and the independent debugger read this same portable configuration. The debugger does not automatically scan or accept folder suggestions. Reopen the executable in an existing debugger session after changing its runtime settings.

#### Different paths have different purposes

| Setting | Purpose |
| --- | --- |
| Working directory (`bin`) | Starting directory for relative runtime paths. |
| Data directory (`data`) | Supplies `COB_FILE_PATH` for COBOL runtime data-file access. |
| Compiler COPY paths | Locate copybooks during compilation; unrelated to this runtime field. |
| GixSQL paths | Locate the SQL preprocessor, SQL copybooks and libraries. |
| SQLite datasource URL | Selects the database file through the database driver; not controlled by `COB_FILE_PATH`. |

Keep explicit relative filenames consistent with the working directory; do not rely on this field to rewrite paths already containing directories. Absolute filenames identify their own location.

#### GixSQL example

For the supplied `gixsql-example`, use working directory **`bin`** and leave data search folders empty unless the application needs additional COBOL data files. Its COBOL loader opens:

```text
../config/application-sqlite.conf
```

and that profile contains:

```text
sqlite://../build/application.db
```

Both paths are intended to resolve from `bin/`. Running from the project root instead can make the configuration-file open fail with status 35. Adding `config` or `build` to the data-search field is not the fix: restore the intended working directory. An inherited `DB_CONFIG_FILE` can separately override the profile chosen by the example program.

A displayed `.cbsql` maps to its unique original source under `src`; for a
copybook, the selected executable identifies the source to rebuild. Ambiguous
sources require manual selection. Only the selected source is compiled; build
other required modules separately or use the IDE's full project rebuild.
Callable modules are not launched directly: select their caller executable.
Saved project settings and IDE preferences are not changed.

## GixSQL programs

GixSQL converts embedded SQL into `.cbsql` COBOL source, which `cobc` compiles and
links. **Select the binary with Executable**, not the original `.cbl` or generated
`.cbsql`. Source selection normally opens the matching `.cbsql` automatically.
Original `.cbl` line mapping through SQL expansion is not implemented.

Recognized projects use the internal GixSQL preprocessing/link pipeline. Otherwise,
use the example/project build script with its include and library settings.
The `gixsql-example` is included among OpenCobolIDE's examples; use the copy in
your own installation. Set the debug flags explicitly in its Project compiler
settings dialog as described above, then rebuild through the IDE rather than
creating a separate manual build.

For an optional manual Linux build, after normal preprocessing has produced
`build/database-test.cbsql`:

```bash
cd "/path/to/gixsql-example"
mkdir -p build/debug
cd build/debug
cobc -x -g -fsource-location -ftraceall -O0 -save-temps \
  -I /usr/share/gixsql/copy \
  -I ../../copybooks \
  -L /usr/lib -lgixsql \
  -o ../../bin/database-test-debug \
  ../database-test.cbsql
```

Adapt GixSQL installation paths. This keeps the original executable and retains
generated files in `build/debug`; the new executable remains in `bin` so relative
runtime configuration paths work. Prefer the IDE build for extra dependencies.

## Flowcharts and PDF export

Click **Flowchart** after source selection. The popup uses traditional symbols:

| Shape | Meaning |
| --- | --- |
| Oval | Start/end |
| Rectangle | Action or calculation |
| Diamond | IF decision |
| Parallelogram | Input/output |

Green arrows mean Yes; orange means No. Other connection colors separate paths.
Overlapping spans use spaced tracks and merges use distinct arrival points.
White gaps make crossings visible; a crossing is not a junction.

Yellow marks the current paused block; light blue marks earlier observed pauses.
**These are source-derived possible paths, not a complete execution trace.**
Continue can execute unobserved blocks between stops. Running/exiting clears the
current yellow highlight; changing source rebuilds the chart and clears history.

Use Zoom +/−, Reset zoom, drag-to-pan and scrollbars. Double-click a block to show
its COBOL line. Clear observed pauses resets the chart history.

The parser supports straight-line statements and explicit nested IF/ELSE/END-IF.
PERFORM loops, EVALUATE, GO TO, SEARCH, paragraph calls, implicit-scope IFs and
same-line statements are not fully modelled; unsupported control flow produces
a **partial chart** warning. Variables are not displayed inside chart blocks.

### Export PDF

Click **Export PDF** in the popup and choose a filename. It exports the entire
chart, independent of current zoom/scroll, as vector text/lines on **portrait A4**.
Colors, execution highlights, a legend, warnings and page numbers are retained.
Long charts break through gaps between blocks; wide charts use horizontal tiles
rather than unreadably small labels. Row/column numbers indicate tile order;
arrows at page edges continue on adjacent tiles.

The export reports success/failure and uses a temporary file before replacing
the destination. Qt's PDF writer needs no additional Python PDF library.

## Session logs

Each GUI session writes a timestamped JSON Lines file. Source checkouts use:

```text
logs/debug-YYYYMMDD-HHMMSS-xxxxxxxx.jsonl
```

Installed packages use `~/.local/state/cobgdb-python/logs/` (or the configured
`XDG_STATE_HOME`). Find its filename beside the source filename, hover for the full path, or click
**Open log file**. The Debugger tab also announces the full path.

Each record has an ISO timestamp with local UTC offset, `kind` and `data`, and is
flushed immediately. Logs include commands, backend events, variable snapshots,
program input/output, stderr, compiler messages, and session start/end.
Launch environment values are redacted, but input and variable values are stored;
review a log before sharing it. Logs are ignored by Git and are not automatically
rotated/deleted. Logging errors are reported without stopping the GUI.
Backend-only operation does not create these GUI session logs.

## Examples

See the [examples guide](examples/README.md), in the suggested learning order:

| Example | Focus | Guide |
| --- | --- | --- |
| Hello | First breakpoint, stepping, COUNTER changes | [Hello guide](examples/hello/README.md) |
| Easter | ACCEPT, calculations, grouped fields and reports | [Easter guide](examples/easter/README.md) |
| World Cities | GixSQL cursor, COPY members, row-by-row inspection | [World Cities guide](examples/worldcities/README.md) |

Each example has its own source/build folders. Existing Easter reports are in
`examples/easter/build/`; rebuild after moving source files.

World Cities includes the required query/error-report programs, copybooks,
original input files and an **unchanged full database snapshot**. Build it with:

```bash
python3 examples/worldcities/build_demo.py
```

Select `examples/worldcities/bin/select-greek-cities` in the debugger. Expected
result: **126 Greek cities**. This standalone example uses its own build script,
not IDE configuration. It requires GixSQL's SQLite driver but no database server
or full-project download. See its guide for environment variables and paths.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `build_editable` missing | Confirm setuptools >=64 in `pyproject.toml`, then reinstall. |
| Python environment is externally managed | Use the virtual environment installation above. |
| `cobc` / `gdb` missing | Check PATH in the environment that launches the GUI. |
| Source file rejected as executable | Select the linked binary; open `.cbl`/`.cbsql` through Source. |
| Pending breakpoint / source not found | Rebuild with debug flags at the current source location and keep generated files. |
| Program is not being run | Run it and wait for a pause before stepping/inspection. |
| Input echoed but no progress | Resume if paused before ACCEPT. |
| Same line after stepping | Separate statements, loop visits, breakpoints or the internal-step limit can stop on the same line. Inspect values and the stop reason. |
| Variables unavailable | Pause in user code, retain matching C/headers and inspect field errors; runtime frames or ambiguous copybook ownership may lack metadata. |
| Finish stops repeatedly | Active breakpoints are respected. Remove unwanted ones before finishing. |
| SQL example uses unexpected database | Check inherited `DB_CONFIG_FILE` and the program's working directory. |
| Project cannot compile | Inspect Compiler output and `config/project.json`; check compiler/GixSQL tools, paths and source overrides. No IDE installation is needed. |
| Log not visible | Look beside the source path or in Debugger; check `logs/` write permission. |
| GDB tracing denied | The OS/execution environment must permit tracing a child process. |
| GDB timeout | Restart the session/GUI; state may be uncertain. |
| Qt accessibility warning | If the window opens and works, the warning is separate from debugger/compiler errors. |

## Platform support and limitations

| Feature | Linux | Windows |
| --- | --- | --- |
| GUI, source view, breakpoints, variables, flowchart and logs | Locally tested | Runtime verification pending |
| Compilation and GDB execution | Locally tested | Matching toolchain required; verification pending |
| Program input/output | Embedded PTY with ACCEPT/DISPLAY | Embedded input pending; output requires native validation |
| Project compiler / PDF export | Locally tested | Verification pending |
| CI configuration | Test workflow configured | Test workflow configured |

CI configuration alone does not establish successful Windows runs. Multi-monitor
window behavior needs real-desktop verification beyond headless size checks.
Source decoding prefers UTF-8 with a CP1253 fallback; encoding selection is not
configurable. Stepping and source mapping rely on compiler metadata and are not
a complete COBOL semantic model. The JSON API is not yet frozen.

Remaining work includes Windows console support, broader dynamic-module/runtime
stepping, complete variable formats/arrays/scopes, standalone build-option UI,
source encodings, breakpoint relocation/persistence, and stronger timeout and
process-tree recovery. A full IDE Debug/Release build profile remains future work.

## Backend protocol and development

### Architecture

```text
PyQt5 GUI / independent project compiler
                  ↕ JSON Lines
          Python debugger backend
                  ↕ GDB/MI2
                 GDB
                  ↕
          Compiled COBOL program
```

For backend-only installation/startup:

```console
python -m pip install -e .
python -m cobgdb_python.backend
```

### JSON protocol version 1

UTF-8 JSON Lines over stdin/stdout; stdout is reserved for protocol messages.
Requests carry `id`, `command`, and optional `arguments`. Responses carry the
same ID, `ok`, and `result` or `error`. Events can precede responses; correlate by
ID rather than arrival order. Execution acknowledgements do not imply completion:
wait for stopped/exited events. Requests are processed serially in one session.

Example requests, sent as execution state permits:

```json
{"id":1,"command":"launch","arguments":{"executable":"/absolute/path/easter"}}
{"id":2,"command":"add_breakpoint","arguments":{"file":"/absolute/path/easter.cbl","line":79}}
{"id":3,"command":"run"}
{"id":4,"command":"input","arguments":{"text":"2031"}}
{"id":5,"command":"continue"}
{"id":6,"command":"cobol_variables"}
{"id":7,"command":"shutdown"}
```

| Command | Arguments / result |
| --- | --- |
| `launch` | `executable`; optional `cwd`, `gdb`, `arguments` string array, `tty`, string `environment` map. Returns optional `source`, `sources`, `source_notice`. |
| `run`, `continue`, `next`, `step`, `finish`, `pause` | Execution control; GUI `next` is Next COBOL line and `step` is Step into external CALL. |
| `add_breakpoint` | `file`, positive `line`; returns GDB breakpoint details. |
| `remove_breakpoint` | Numeric `number`. |
| `cobol_variables` | Rows with `name`, `value`, `format`, `size`, optional `error`; used by GUI. |
| `variables` | Raw GDB locals. |
| `stack` | Raw GDB frames. |
| `evaluate` | GDB `expression`; intended for trusted local clients. |
| `input` | `text`, optional `newline` (true by default); UTF-8 to managed terminal. |
| `reset` | Closes GDB/terminal but keeps the backend alive. |
| `shutdown` | Closes the session and exits the backend. |

Events include ready (protocol_version), running, stopped, exited, output,
notification, diagnostic and backend_gdb_exited. Output channels include program
and GDB MI stream markers. Windows paths require JSON escaping or forward slashes;
paths resolve on the backend machine. An external tty bypasses managed input.

Source mapping parses generated `Line:` comments and `#line` directives. Mapped
stops expose COBOL `location`/`frame` and preserve the C `generated_location`.
Unmapped C stops have null location and `source_mapping: unavailable`. Other
payloads still expose GDB structures and can evolve.

### Tests

```console
python -m unittest discover -s tests -v
```

Optional GUI/PDF tests need PyQt5 and can use `QT_QPA_PLATFORM=offscreen` on Linux.
Live integration tests need GDB, cobc and tracing permission; tests skip when
required tools are absent. Project compiler tests run the worker in isolated Python
without site-packages to verify independence from the IDE and Qt. Test coverage includes MI parsing, protocol errors, discovery,
source mapping, stepping/calls/loops, copybook variables, project paths, routing,
PDF output and window layout. Additional local checks exercised Easter input,
GixSQL builds and row inspection; not every desktop scenario is automated.

### Source layout

| Module/path | Role |
| --- | --- |
| `frontend.py` | GUI, source/check boxes, popup, compiler and JSON client. |
| `backend.py` | JSON server, GDB commands/events, terminal and memory reads. |
| `mi.py` | GDB/MI parser. |
| `source_map.py`, `source_discovery.py` | COBOL locations and main source selection. |
| `variables.py` | Generated field metadata and supported decoding. |
| `ide_project.py` | Independent portable project configuration reader. |
| `project_build.py`, `project_source.py` | Internal compiler worker and COBOL/SQL inspection. |
| `flow_model.py`, `flow_routes.py`, `flowchart.py` | Source graph, connection routing, popup/PDF. |
| `session_log.py` | Timestamped logs. |
| `examples/`, `tests/` | Learning projects and regression tests. |
| `.github/workflows/tests.yml` | Linux/Windows test configuration. |

Python modules are under `cobgdb_python/`. See [development notes](DEVELOPMENT.md)
for implementation-only details. The protocol follows the official
[GDB/MI output syntax](https://sourceware.org/gdb/current/onlinedocs/gdb.html/GDB_002fMI-Output-Syntax.html).


### GUI launcher arguments

```bash
cobgdb-python-gui
cobgdb-python-gui /path/to/program
cobgdb-python-gui /path/to/program --source /path/to/source.cbl
```

No arguments opens the GUI for manual selection. An executable argument loads that binary after the backend starts, without running it automatically. The optional source identifies the original COBOL program and its saved project configuration. Invalid paths are reported before opening the GUI. The independent engine/compiler are unchanged.


### Interface icons

Toolbar controls, Debugger/Program output/JSON events/Compiler tabs, program input, log access and flowchart buttons have icons before their labels. Desktop theme icons fall back to standard Qt icons when no matching theme icon is installed. The wrapping toolbar and existing button labels remain in use.


### Default project runtime directory

Project executables run with the project's bin/ folder as the working directory by default, including when runtime settings have not been accepted. An explicitly saved config/project.json runtime working_directory overrides it; an omitted working_directory defaults to bin. Data search paths remain separately configurable. Computing a build plan does not require bin to exist before the first build. No runtime files or databases are moved.


### Native RPM and Windows release packaging

Fedora 44 and Mageia 10 specs are provided under packaging/fedora and packaging/mageia. Matched two-application transfer kits are created from the OpenCobolIDE repository's packaging/make-modern12-transfer-kits.py; the IDE's packaging/RPM_MODERN12.md describes native prerequisites, build commands and collection of binary/source RPMs and logs. Native target builds/install/desktop tests remain pending. These are private local-test specs, not approved distro-repository packages; the existing unspecified project-license notice is retained as LicenseRef-Local-Test-Only.

The application version remains 0.1.0, with native RPM build revision 1. Windows release deliverables will be a standalone .exe and an Inno Setup .exe installer; Windows build/testing and publication remain separate pending steps.

### Program terminal and graphical programs

Use **Program output** and the input box for terminal-style COBOL programs. Graphical COBOL programs open their own windows. See [the graphical score example](examples/gui/README.md), [release notes](RELEASE_NOTES.md) and [Windows build instructions](packaging/windows/README.md).
