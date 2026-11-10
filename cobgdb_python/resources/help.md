# COBOL Debugger Help

## Start a debug session

1. Build your COBOL executable with `-g -fsource-location -ftraceall -O0 -save-temps`. Keep the generated C and headers from that build with the executable.
2. Choose **Executable** to load the binary. Use **Source** if COBOL Debugger cannot find its COBOL source.
3. Click a source line's breakpoint box, then choose **Run**. Use **Next COBOL line** to step and **Continue** to resume.
4. Use **Variables** at a pause to inspect the current COBOL values.

## Enter program input

Read program output in **Program output**. On Linux, type values or menu choices in the input box and click **Send input**, or press Enter. Continue past an ACCEPT breakpoint so the program can read the value. Graphical programs use their own windows. Embedded keyboard input on Windows is pending.

## Projects and examples

For an OpenCobolIDE project, enable Debug compilation and rebuild. Keep the matching generated files in the project's `debug_data/` directory. When started without an executable, COBOL Debugger shows a popup with the required flags. Programs normally run from `bin/`.

Open **Help → About COBOL Debugger → Examples** to find the installed Hello, Easter, Countries, Graphical score and EU Cities examples. Open the example's README for its build and debugging steps.
