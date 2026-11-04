# World Cities: select Greek cities

A small program set for learning cobgdb-python with GixSQL, SQLite, COPY members,
cursor fetches, and changing COBOL values. The program/copybooks come from the
local `worldcities-cobol` project. **The dataset is not reduced or altered.**

The bundled SQLite snapshot contains the original tables, indexes and rows:

| Table | Rows |
| --- | ---: |
| countries | 268 |
| cities | 26,569 |
| cities_new (used by the query) | 26,570 |

The query selects the **126** rows in `cities_new` whose ISO2 is `GR`. The snapshot
is a copy made through SQLite's backup API; its binary file bytes may differ
from the original. Original `countries.txt` and `worldcities.txt` files are also
included unchanged. No full dataset download or database server is required.

## Files

```text
src/select-greek-cities.cbl      main program: connect, fetch, display, count
src/sql-error-handler.cbl       separately compiled callable error reporter
copybooks/DB-CONFIG-WS.CPY      working storage (uppercase name required by gixpp)
copybooks/db-config-select.cpy  config-file declaration
copybooks/db-config-fd.cpy      config-file record
copybooks/db-config-procedure.cpy  configuration and error-report paragraphs
data/worldcities-sqlite.db      full original database snapshot
data/countries.txt             original country data
data/worldcities.txt           original city data
build_demo.py                   preprocess, compile, copy local database, configure
```

The build creates `bin/`, `build/`, and `config/worldcities-sqlite.conf` locally.
These generated files are ignored by Git. The bundled snapshot stays in `data/`;
the example uses its own working copy at `build/worldcities-sqlite.db`. Existing
working copies are preserved on rebuild. The original World Cities project is
never read or modified by the example's build/run commands.

## Requirements

- Python 3.10+, GnuCOBOL (`cobc`), GDB and the debugger GUI dependencies.
- GixSQL preprocessor (`gixpp`), SQLCA copybook, runtime and SQLite driver.
- SQLite support in Python (normally included); no sqlite3 command-line tool needed.

Build from the debugger repository:

```bash
cd ~/cobgdb-python
python3 examples/worldcities/build_demo.py
```

Default SQLCA location is `/usr/share/gixsql/copy`; libraries use the system
linker's search directories. For another installation, set `GIXSQL_COPY_DIR`,
`GIXSQL_LIBRARY_DIR`, `COBC`, or `GIXPP` as needed before building. Windows users
must set tool/copybook/library paths for their installation; this example was
verified on Linux, not Windows.

**ALL compiled programs/modules use `-g -fsource-location -ftraceall -O0
-save-temps`. Generated C/headers are retained for stepping and variable display.**
The main program is preprocessed into `build/select-greek-cities.cbsql`, linked
with GixSQL, and output to `bin/select-greek-cities` (`.exe` on Windows). The
error reporter becomes `bin/sql-error-handler.so` (`.dll` on Windows).
Use this build script, not the GUI's plain single-source compile action: GixSQL
needs its preprocessing, include directories, runtime link, and error module.

## Run without the debugger

```bash
cd ~/cobgdb-python/examples/worldcities/bin
unset DB_CONFIG_FILE
./select-greek-cities
```

Default config lookup is relative to this `bin` working directory. The generated
config uses `sqlite://../build/worldcities-sqlite.db`; credentials are blank for
SQLite. An inherited `DB_CONFIG_FILE` overrides that config, so unset it when
using this example. The output lists Greek cities and ends with:

```text
GREEK CITIES: 000000126
```

## Debugging walkthrough

1. Build as above. From the repository, unset `DB_CONFIG_FILE`, then start:
   `python3 -m cobgdb_python.frontend`.
2. Click **Executable** and select
   `examples/worldcities/bin/select-greek-cities`.
3. The generated `.cbsql` source should open automatically. If needed, select
   `examples/worldcities/build/select-greek-cities.cbsql` with **Source**.
4. Check a line near `MAIN-PROCEDURE` and click **Run**. GDB can move a breakpoint
   to the next executable line; the yellow highlight shows the actual stop.
5. Use **Next COBOL line** to follow configuration loading. COPY member source
   opens as execution enters it, and variables remain available.
6. Add a breakpoint on the DISPLAY statement under `DISPLAY-CITY` and Continue.
   Inspect `CITY-NAME`, `COUNTRY-NAME`, `CITY-ISO2`, `POPULATION`, and `ROW-COUNT`.
7. Continue to the same breakpoint for the next fetched city. Observe changed
   fields highlighted in the variables popup. ROW-COUNT grows with each row.
8. Remove loop breakpoints to run uninterrupted. **Continue** completes the
   query; **Finish** also respects breakpoints and can run to exit when invoked
   in the main program. Final output should count 126 cities.

In the locally tested GixSQL version, generated source has MAIN-PROCEDURE at line
54, `ADD 1 TO ROW-COUNT` at 117, and the city DISPLAY at 236. **Find the statement
text instead of relying on these numbers across preprocessor versions.**
Breakpoints in generated `.cbsql` are not automatically translated to the
original `.cbl` SQL source. COPY members have their own source locations.

`SQL-ERROR-HANDLER` is called only on an SQL error; a normal successful query does
not enter it. It is included so the example has its required error dependency.
**Step into external CALL** applies to such COBOL program calls when debug entry
information is available. It is not an internal-PERFORM finish action, and a
module loaded only at runtime may still need a manual breakpoint.

The optional **Flowchart** is partial for this program because PERFORM loops,
paragraph calls and SQL-generated control flow are not fully modelled. Use
source stepping, variables, and session logs as the primary learning tools.

## Verification

The packaged example built independently, returned 126 Greek cities, and left
the original database/project unchanged. All three table row counts in the
snapshot matched the original. Compiler outputs are local to the example;
rebuild after moving it so debug paths match its new location.
