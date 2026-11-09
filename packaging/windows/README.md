# COBOL Debugger 0.1.0 for Windows 11 x64

Extract the dedicated `cobgdb-python-0.1.0.tar.gz` source archive and work from its root. Build Windows separately on Windows 11 x64. The Windows release downloads are the standalone executable and Inno Setup installer.

On Windows 11, use 64-bit Python with PyQt5 and PyInstaller 6.9 or newer. Use your installed Inno Setup 7 command-line compiler, ISCC.exe.

```powershell
python -m pip install "PyQt5>=5.15,<6" "PyInstaller>=6.9,<7"
.\packaging\windows\build.ps1 -InnoCompiler 'C:\Program Files\Inno Setup 7\ISCC.exe'
```

Adjust the compiler path to match your Inno Setup 7 installation.

The script produces cobol-debugger.exe, COBOL-Debugger-0.1.0-win11-x64-setup.exe and SHA256SUMS in dist/windows by default. The single executable includes the GUI and JSON protocol backend. It uses a console-capable bootloader for worker pipes. GDB, GnuCOBOL, its C compiler and optional GixSQL come from the native toolchain. The per-user installer registers the launcher so OpenCobolIDE can discover it.

Test no-argument, executable-only and executable-plus-source launches. Run a COBOL program that uses ACCEPT and DISPLAY and inspect its output in Program output. Embedded keyboard input on Windows remains pending. Build and debug the graphical score example in examples/gui. Verify the Yes and No branches and variables at a breakpoint. Check project debug rebuild, IDE launch, installation and uninstallation on a Windows test profile. Windows compilation and native verification are pending. The project currently carries a private local-test packaging notice.

[PyInstaller command options](https://pyinstaller.org/en/stable/usage.html) · [Inno Setup compiler options](https://jrsoftware.org/ishelp/topic_compilercmdline.htm)


Release transfer folders
------------------------
Successful native package builds create `<system>-<YYYY-MM-DD>-release` and a matching `.tar.gz` plus SHA256 checksum. Copy the complete folder or archive back to Mint. It contains native packages, current source snapshots, Git history/provenance when available, build scripts, and build logs. Each application has its own subfolder; repeated builds preserve earlier results. Set `RELEASE_OUTPUT_BASE` to choose a shared destination (or use the existing output option on Windows). `RELEASE_DATE` can explicitly override the local build date. Collection never commits, pushes, installs, or publishes. Review lint results, native tests, source changes and release notes on Mint before publishing.
