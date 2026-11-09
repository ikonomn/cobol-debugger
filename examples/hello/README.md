# Hello

Add a breakpoint, step through an ADD, and watch COUNTER change.

Open a terminal in this example folder and build:

```bash
mkdir -p bin
cd bin
cobc -x -g -fsource-location -ftraceall -O0 -save-temps -o hello ../hello.cob
cobol-debugger ./hello --source ../hello.cob
```

Set a breakpoint on `ADD 1 TO COUNTER` and click **Run**. COUNTER starts at 1.
Click **Next COBOL line** and check that it becomes 2. Click **Continue** to see
`Counter: 2` in **Program output**.
