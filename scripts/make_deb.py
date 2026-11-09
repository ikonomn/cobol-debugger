#!/usr/bin/env python3
"""Build a local Debian package with standard library and dpkg-deb only."""
import argparse
import hashlib
import gzip
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from stage_examples import stage_examples
from release_bundle import collect, native_system


def write(root, name, content, mode=0o644):
    path = root/name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    path.chmod(mode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    version = re.search(r'^version\s*=\s*"([^"]+)"', (source/'pyproject.toml').read_text(), re.M)[1]+'-15'
    output = (args.output or source/'dist').resolve()
    output.mkdir(parents=True, exist_ok=True)
    package = output/f'cobol-debugger_{version}_all.deb'
    with tempfile.TemporaryDirectory(prefix='cobgdb-deb-') as folder:
        root = Path(folder)
        module = root/'usr/lib/python3/dist-packages/cobgdb_python'
        module.mkdir(parents=True)
        for file in sorted((source/'cobgdb_python').glob('*.py')):
            shutil.copyfile(file, module/file.name)
            (module/file.name).chmod(0o644)
        shutil.copytree(source/'cobgdb_python/resources', module/'resources')
        icon_dir = root/'usr/share/icons/hicolor/scalable/apps'
        icon_dir.mkdir(parents=True)
        shutil.copyfile(module/'resources/cobgdb.svg', icon_dir/'cobol-debugger.svg')
        for command, target in [('cobol-debugger-backend', 'backend'), ('cobol-debugger', 'frontend')]:
            write(root, 'usr/bin/'+command,
                  f'#!/usr/bin/python3\nfrom cobgdb_python.{target} import main\nmain()\n', 0o755)
        write(root, 'usr/share/applications/cobol-debugger.desktop', '''[Desktop Entry]
Type=Application
Name=COBOL Debugger
Comment=Debug GnuCOBOL programs with source stepping and variable inspection
Exec=cobol-debugger
Icon=cobol-debugger
Terminal=false
Categories=Development;Debugger;
StartupNotify=true
''')
        docs = root/'usr/share/doc/cobol-debugger'
        docs.mkdir(parents=True)
        for name in ('README.md', 'DEVELOPMENT.md', 'RELEASE_NOTES.md'):
            shutil.copyfile(source/name, docs/name)
        stage_examples(docs/'examples')
        write(root, 'usr/share/doc/cobol-debugger/README.Debian', '''COBOL Debugger

Launch from the applications menu or run cobol-debugger.
Optionally: cobol-debugger /path/to/executable [--source /path/to/source.cbl]
The JSON backend command is cobol-debugger-backend.
Logs: ${XDG_STATE_HOME:-$HOME/.local/state}/cobgdb-python/logs/
No OpenCobolIDE installation is required.
Help > About COBOL Debugger > Examples opens the installed examples and their index.
Examples are copied to ~/COBGDB-examples on launch; existing files are preserved.
GixSQL must be installed separately when compiling SQL programs.
This is a local test package, not a published distribution.
''')
        write(root, 'usr/share/doc/cobol-debugger/copyright',
              (source/'packaging/LICENSE.local-test').read_text(encoding='utf-8')
              + '\n' + (source/'LICENSE').read_text(encoding='utf-8'))
        changelog = f"""cobol-debugger ({version}) unstable; urgency=medium

  * Show call stack frames, scope COBOL variables to COBOL stops, and open original C helpers in a separate window.
  * Add offline Help, About, installed example access and a launcher icon.
  * Restore embedded program output and input and ship all five examples.
  * Preserve explicit project cwd overrides and themed interface icons.
  * Preserve optional executable and --source launcher arguments.
  * Use EU Cities as the shared SQL example and ship GeoNames attribution.
  * Rename the application, package and commands to COBOL Debugger.
  * Show required debug flags at standalone startup.
  * Remove compilation controls from the debugger window.

 -- Local Package Builder <local-build@cobol-debugger.invalid>  Mon, 09 Nov 2026 12:00:00 +0000
"""
        (docs/'changelog.Debian.gz').write_bytes(gzip.compress(changelog.encode(), mtime=0))
        for name, description, invocation in [
            ('cobol-debugger-backend', 'JSON debugger backend for GnuCOBOL', 'Reads newline-delimited JSON requests from standard input and writes JSON events to standard output.'),
            ('cobol-debugger', 'graphical debugger for GnuCOBOL', 'Opens the standalone debugger window. An optional executable argument loads it; --source selects its original COBOL source. Without arguments, select the executable in the GUI.')]:
            man = f""".TH {name.upper()} 1 "2026-11-04" "cobol-debugger {version}"
.SH NAME
{name} \- {description}
.SH SYNOPSIS
.B {name}
.SH DESCRIPTION
{invocation}
.SH FILES
/usr/share/doc/cobol-debugger/README.md
.SH SEE ALSO
.BR gdb (1),
.BR cobc (1)
"""
            manpath = root/f'usr/share/man/man1/{name}.1.gz'
            manpath.parent.mkdir(parents=True, exist_ok=True)
            manpath.write_bytes(gzip.compress(man.encode(), mtime=0))
        for path in root.rglob('*'):
            if path.is_dir():
                path.chmod(0o755)
            elif not path.is_relative_to(root/'usr/bin'):
                path.chmod(0o644)
        installed_size = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())//1024+1
        write(root, 'DEBIAN/control', f'''Package: cobol-debugger
Version: {version}
Conflicts: cobgdb-python
Replaces: cobgdb-python
Section: devel
Priority: optional
Architecture: all
Maintainer: Local Package Builder <local-build@cobol-debugger.invalid>
Depends: python3 (>= 3.10), python3-pyqt5, gdb
Recommends: gnucobol
Installed-Size: {installed_size}
Description: Standalone graphical debugger for GnuCOBOL
 Follow COBOL execution, set breakpoints and inspect variable values.
 Includes an independent JSON GDB/MI backend.
''')
        entries = []
        for file in sorted((root/'usr').rglob('*')):
            if file.is_file():
                entries.append(hashlib.md5(file.read_bytes()).hexdigest()+'  '+file.relative_to(root).as_posix())
        write(root, 'DEBIAN/md5sums', '\n'.join(entries)+'\n')
        build_log = output/'cobol-debugger-build.log'
        with build_log.open('w', encoding='utf-8') as log:
            subprocess.run(['dpkg-deb', '--root-owner-group', '-Zxz', '--build', str(root), str(package)],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    package.with_suffix(package.suffix+'.sha256').write_text(f'{digest}  {package.name}\n')
    collect(native_system(), 'cobol-debugger', output, source, [str(package), str(package)+'.sha256', str(build_log)])
    print(package)


if __name__ == '__main__':
    main()
