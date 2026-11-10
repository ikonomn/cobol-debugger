# Easter

Enter a year and calculate the Eastern Church movable feasts.

Open a terminal in this example folder and build:

```bash
mkdir -p bin
cd bin
cobc -x -g -fsource-location -ftraceall -O0 -save-temps -o easter ../src/easter.cbl
cobol-debugger ./easter --source ../src/easter.cbl
```

Set breakpoints at the year ACCEPT and the next executable statement. Click
**Run**. At the ACCEPT breakpoint, click **Continue**, enter `2031`, and click
**Send input**. At the next stop, inspect ETOS. Continue to finish and check
**Program output**. The program writes `MV_FEASTS2031.TXT` in the example folder.
