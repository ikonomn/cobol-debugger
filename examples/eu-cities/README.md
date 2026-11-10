# EU Cities

Step through a GixSQL cursor over 5,398 cities in the 27 EU countries.
The SQLite database uses the official GeoNames snapshot. See [data sources](../DATA-SOURCES.md).

With GnuCOBOL, GixSQL and its SQLite driver installed, run from this folder:

```bash
python3 build_demo.py
cd bin
unset DB_CONFIG_FILE
cobol-debugger ./select-eu-cities
```

Set a breakpoint on the city DISPLAY statement and click **Run**. Inspect
`CITY-NAME`, `CITY-ISO2`, and `ROW-COUNT` at successive stops. Remove the
breakpoint and continue to see `EU CITIES: 000005398`.

The program reads the bundled database in `data/` while running from `bin/`.
In OpenCobolIDE, open this example as a project and choose **Rebuild Project**
so the executable and its SQL error handler are both built. If the debugger needs a source selection,
choose `build/select-eu-cities.cbsql`.
