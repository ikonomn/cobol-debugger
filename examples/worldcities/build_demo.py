"""Build a small COBOL example using an unchanged snapshot of the World Cities dataset."""
import argparse
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
DEBUG = ['-g', '-fsource-location', '-ftraceall', '-O0', '-save-temps']

def run(command, cwd):
    print('Running:', ' '.join(map(str, command)), flush=True)
    subprocess.run(list(map(str, command)), cwd=cwd, check=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    cobc = os.environ.get('COBC', 'cobc')
    gixpp = os.environ.get('GIXPP', 'gixpp')
    for tool in [cobc, gixpp]:
        if not shutil.which(tool):
            parser.error(f'Tool not found: {tool}. Add it to PATH or set COBC/GIXPP.')
    gixcopy = Path(os.environ.get('GIXSQL_COPY_DIR', '/usr/share/gixsql/copy')).resolve()
    if not (gixcopy/'SQLCA.cpy').exists() and not (gixcopy/'sqlca.cpy').exists():
        parser.error(f'SQLCA copybook not found in {gixcopy}; set GIXSQL_COPY_DIR')
    build, binary = ROOT/'build', ROOT/'bin'
    build.mkdir(exist_ok=True);binary.mkdir(exist_ok=True)
    database = build/'worldcities-sqlite.db'
    if not database.exists():
        # Copy the bundled full dataset; never modify the original project database.
        with tempfile.NamedTemporaryFile(dir=build, suffix='.db', delete=False) as temp:
            replacement = Path(temp.name)
        try:
            connection = sqlite3.connect(replacement)
            try:
                snapshot = sqlite3.connect((ROOT/'data/worldcities-sqlite.db').as_uri()+'?mode=ro', uri=True)
                try:
                    snapshot.backup(connection)
                finally:
                    snapshot.close()
            finally:
                connection.close()
            replacement.replace(database)
        finally:
            if replacement.exists():replacement.unlink()
    config = ROOT/'config/worldcities-sqlite.conf'
    config.write_text('DATASRC=sqlite://../build/worldcities-sqlite.db\nDATASRC_USR=\nDATASRC_PWD=\n')
    includes = ['-I', str(ROOT/'copybooks'), '-I', str(gixcopy)]
    source = ROOT/'src/select-greek-cities.cbl'
    preprocessed = build/'select-greek-cities.cbsql'
    run([gixpp, '-e', '-S', '-z', 'a', '-P', 'varchar', *includes,
         '-i', source, '-o', preprocessed], build)
    extension = '.dll' if os.name=='nt' else '.so'
    run([cobc, '-m', *DEBUG, *includes, '-o', binary/('sql-error-handler'+extension),
         ROOT/'src/sql-error-handler.cbl'], build)
    executable = binary/('select-greek-cities.exe' if os.name=='nt' else 'select-greek-cities')
    libraries = ['-lgixsql']
    if os.environ.get('GIXSQL_LIBRARY_DIR'):
        libraries = ['-L', os.environ['GIXSQL_LIBRARY_DIR'], *libraries]
    run([cobc, '-x', *DEBUG, *includes, '-o', executable, preprocessed, *libraries], build)
    print(f'\nExecutable: {executable}\nSource: {preprocessed}\nWorking directory: {binary}')
    print('Expected result: GREEK CITIES: 000000126')

if __name__=='__main__':main()
