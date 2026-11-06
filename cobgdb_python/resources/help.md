# COBGDB Help

## Start a debug session

1. Build your COBOL executable with `-g -fsource-location -ftraceall -O0 -save-temps`. Keep the generated C and headers from that build with the executable.
2. Choose **Executable** to load the binary. Use **Source** if COBGDB cannot find its COBOL source.
3. Click a source line's breakpoint box, then choose **Run**. Use **Next COBOL line** to step and **Continue** to resume.
4. Use **Variables** at a pause to inspect the current COBOL values.

## Enter program input

Type values and menu choices in the native program terminal. Continue past an ACCEPT breakpoint before typing. If Linux reports that it is using the embedded terminal, use the debugger's input box and **Send input**. Graphical COBOL programs use their own windows.

## Projects and examples

For an OpenCobolIDE project, enable Debug compilation and rebuild. Keep the matching generated files in the project's `debug_data/` directory. **Compile with debug** uses saved project settings for recognized projects. Programs normally run from `bin/`.

Open **Help → About COBGDB → Examples** to find the installed Hello, Easter, Countries, Graphical score and World Cities examples. Start with the examples index and copy the example you want to a writable location before building it.
