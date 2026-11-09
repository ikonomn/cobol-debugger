# Countries

Read and display country records from `data/countries.txt`.

Open a terminal in this example folder and build:

```bash
mkdir -p bin
cd bin
cobc -x -g -fsource-location -ftraceall -O0 -save-temps -o readfilecob ../src/readfilecob.cbl
cobol-debugger ./readfilecob --source ../src/readfilecob.cbl
```

Set a breakpoint on a READ or DISPLAY statement and click **Run**. Inspect the
record as you step, then check **Program output**. The saved project runtime
settings use `data/` as the working directory so the program can find its input.

The input data comes from GeoNames. See [data sources](../DATA-SOURCES.md).
