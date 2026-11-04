# Development notes

## Optional breakpoint toolbar control

The user interface relies on checkbox and line-number clicks. The optional
Toggle breakpoint toolbar button is retained but hidden by default through
`SHOW_BREAKPOINT_BUTTON = False` in `cobgdb_python/frontend.py`. Set it to True
and restart to expose it for development or a future user-requested option.
The F9 shortcut has been removed. Keep these implementation details out of the
user README.

## Linux compiler-settings documentation

User setup must describe the actual Project compiler settings dialog: project
settings enabled, IDE-default flags unchecked, and explicit debug flags. Internal
settings resolution is an implementation detail, not a sequence of UI selections.
The old Preferences/Compiler interface needs review in a future IDE build; this
debugger change does not alter the installed IDE or saved preferences.

## Independent project compiler

ide_project.py reads the portable schema-1 JSON without IDE or Qt imports.
project_build.py executes cobc/gixpp with subprocess argument lists; it requires
no Bash, IDE build scripts or installed IDE. ide_build.py was removed.
The GUI converts the plan environment dictionary to QProcessEnvironment only
at its boundary. The worker rereads saved configuration on every invocation.

Project options and source overrides are implemented locally. IDE-global
QSettings are deliberately excluded; project null/inherit values fall back to
internal defaults and the current process environment. Essential build settings
must be explicit in JSON to reproduce a build independently. The runtime schema
supports accepted working_directory/data_directories, not arbitrary discovery.

PROCEDURE DIVISION USING detection is source-based, not the IDE's global cached
mode override. Source inspection supports COPY recursion, comments, literals and
format directives; it is not a complete COBOL preprocessor. SQL INCLUDE handling
is delegated to gixpp. Build-control flags are rejected in extra flags.

Debug output follows modern12's debug_data/<source-relative-stem>/ convention.
The GCC/Clang prefix-map argument quotes paths for cobc's -A parsing. Other C
compiler toolchains need explicit future verification. Source/module basename
collisions in bin/build remain possible, as in the existing IDE layout.

Tests exercise isolated Python without site-packages, block IDE/Qt imports,
compile executables and modules, build real GixSQL examples, verify debugger
source/variable discovery, and preserve prior output after compiler failure.
Windows execution still requires verification. Keep optional hidden breakpoint
control details in this file rather than the user guide.
