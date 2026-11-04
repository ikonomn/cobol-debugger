"""Internal, shell-free project compiler worker; usable without Qt or the IDE."""
from pathlib import Path
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cobgdb_python.ide_project import DEBUG_FLAGS, build_plan


def run(command, cwd, environment):
    print('$ '+shlex.join(map(str, command)), flush=True)
    # Inherit the worker's output pipe for immediate GUI output and logs.
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def compile_project(plan):
    root = plan.root
    build = root/'build'
    build.mkdir(parents=True, exist_ok=True)
    plan.output.parent.mkdir(parents=True, exist_ok=True)
    flags = list(plan.flags)
    for index, flag in enumerate(flags[:-1]):
        if flag in ('-T', '-t'):
            Path(flags[index+1]).parent.mkdir(parents=True, exist_ok=True)
    source = plan.source
    env = plan.environment
    if plan.sql:
        gixcopy = env.get('GIXSQL_COPY_DIR', '/usr/share/gixsql/copy' if os.name != 'nt' else '')
        if not gixcopy:
            raise ValueError('SQL build requires GIXSQL_COPY_DIR in the environment or project configuration.')
        preprocessed = build/(source.stem+'.cbsql')
        command = [env.get('GIXPP', 'gixpp'), '-e', '-S', '-z', 'a', '-P', 'varchar']
        for directory in dict.fromkeys([gixcopy, *plan.copybook_paths]):
            command.extend(['-I', directory])
        # Only publish a successfully preprocessed source.
        with tempfile.TemporaryDirectory(prefix='.sql-', dir=build) as work:
            target = Path(work)/preprocessed.name
            run([*command, '-i', str(source), '-o', str(target)], root, env)
            os.replace(target, preprocessed)
        source = preprocessed
        flags.extend(['-I', gixcopy])
        library = env.get('GIXSQL_LIBRARY_DIR')
        if library:
            flags.extend(['-L', library])
        flags.append('-lgixsql')
    target = root/'debug_data'/plan.source.relative_to(root).with_suffix('')
    print(f'Project: {root}\nSource: {plan.source}\nDebug compilation: {plan.debug}', flush=True)
    # A failed compiler never replaces the last successful executable or metadata.
    with tempfile.TemporaryDirectory(prefix='.compile-', dir=build) as workspace:
        workspace = Path(workspace)
        compiled = workspace/plan.output.name
        if plan.debug:
            flags.extend(DEBUG_FLAGS)
            prefix_map = f'-fdebug-prefix-map={workspace}={target}'
            # cobc parses -A as C-compiler command text, even though cobc
            # itself is launched without a shell. Preserve spaces in paths.
            quoted = subprocess.list2cmdline([prefix_map]) if os.name == 'nt' else shlex.quote(prefix_map)
            flags.extend(['-A', quoted])
        run([plan.compiler, '-m' if plan.module else '-x', *flags,
             '-o', str(compiled), str(source)], workspace if plan.debug else root, env)
        if not compiled.is_file():
            raise ValueError('Compiler succeeded but did not produce the expected program: '+str(compiled))
        if plan.debug:
            retained = [p for p in workspace.iterdir() if p.suffix in ('.c', '.h')]
            if not any(p.suffix == '.c' for p in retained):
                raise ValueError('Compiler did not retain generated C metadata for this debug build.')
            target.mkdir(parents=True, exist_ok=True)
            for old in target.iterdir():
                if old.is_file() and old.suffix in ('.c', '.h'):
                    old.unlink()
            for artifact in retained:
                shutil.copy2(artifact, target/artifact.name)
            print('Debug C sources and headers: '+str(target), flush=True)
        os.replace(compiled, plan.output)
    print('Output: '+str(plan.output), flush=True)


def main():
    try:
        root, source = map(Path, sys.argv[1:])
        plan = build_plan(source)
        if plan is None or plan.root != root.resolve():
            raise ValueError('The source does not belong to the selected project.')
        compile_project(plan)
        return 0
    except subprocess.CalledProcessError as exc:
        print(f'Build failed: compiler/preprocessor exited with {exc.returncode}', file=sys.stderr, flush=True)
        return exc.returncode if exc.returncode > 0 else 1
    except (OSError, ValueError) as exc:
        print('Build configuration error: '+str(exc), file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
