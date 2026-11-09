"""Build a small COBOL example using a GeoNames SQLite snapshot."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

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
    if not (ROOT/'data/eu-cities-sqlite.db').is_file():
        parser.error('The bundled EU Cities SQLite database is missing.')
    includes = ['-I', str(ROOT/'copybooks'), '-I', str(gixcopy)]
    source = ROOT/'src/select-eu-cities.cbl'
    preprocessed = build/'select-eu-cities.cbsql'
    run([gixpp, '-e', '-S', '-z', 'a', '-P', 'varchar', *includes,
         '-i', source, '-o', preprocessed], build)
    extension = '.dll' if os.name=='nt' else '.so'
    run([cobc, '-m', *DEBUG, *includes, '-o', binary/('SQL-ERROR-HANDLER'+extension),
         ROOT/'src/sql-error-handler.cbl'], build)
    executable = binary/('select-eu-cities.exe' if os.name=='nt' else 'select-eu-cities')
    libraries = ['-lgixsql']
    if os.environ.get('GIXSQL_LIBRARY_DIR'):
        libraries = ['-L', os.environ['GIXSQL_LIBRARY_DIR'], *libraries]
    run([cobc, '-x', *DEBUG, *includes, '-o', executable, preprocessed, *libraries], build)
    print(f'\nExecutable: {executable}\nSource: {preprocessed}\nWorking directory: {binary}')
    print('Expected result: EU CITIES: 000005398')

if __name__=='__main__':main()
