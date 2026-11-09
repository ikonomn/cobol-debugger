#!/usr/bin/env python3
"""Collect a successful native build for transfer to the Mint release machine."""
import argparse
from datetime import date, datetime, timezone
import glob
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import time

EXCLUDED = {'.git', '.local-guidance', '.venv', 'venv', '__pycache__',
            '.pytest_cache', 'build', 'dist', 'logs', 'bin', 'debug_data'}
SOURCE_DIRS = {'open_cobol_ide', 'cobgdb_python', 'scripts', 'packaging',
               'examples', 'test', 'tests', 'doc', 'forms', 'share'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else _digest(stream)


def _digest(stream):
    result = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        result.update(block)
    return result.hexdigest()


def checksums(folder):
    entries = []
    for path in sorted(folder.rglob('*')):
        if path.is_file() and path != folder / 'SHA256SUMS' and not any(
                part.startswith('.') for part in path.relative_to(folder).parts):
            entries.append(digest(path) + '  ' + path.relative_to(folder).as_posix())
    (folder / 'SHA256SUMS').write_text('\n'.join(entries) + '\n', encoding='utf-8')


def source_snapshot(source, destination, app):
    provenance = {'source_directory': str(source), 'revision': None, 'dirty': None}
    try:
        def git(*args):
            return subprocess.check_output(['git', '-C', str(source), *args], stderr=subprocess.DEVNULL)
        if Path(os.fsdecode(git('rev-parse', '--show-toplevel')).strip()).resolve() != source:
            raise ValueError('Not a repository root')
        provenance['revision'] = git('rev-parse', 'HEAD').decode().strip()
        provenance['tags_at_head'] = git('tag', '--points-at', 'HEAD').decode().splitlines()
        refs = ['HEAD'] + ['refs/tags/' + tag for tag in provenance['tags_at_head']]
        git('bundle', 'create', str(destination / 'source-history.bundle'), *refs)
        status = git('status', '--porcelain').decode('utf-8', errors='replace')
        provenance['dirty'] = bool(status)
        (destination / 'GIT_STATUS.txt').write_text(status, encoding='utf-8')
        (destination / 'SOURCE_CHANGES.patch').write_bytes(git('diff', '--binary', 'HEAD'))
        names = [Path(os.fsdecode(n)) for n in git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split(b'\0') if n]
    except (OSError, subprocess.CalledProcessError, ValueError):
        # Exported source trees and Windows machines without Git are supported.
        names = [p.relative_to(source) for p in source.rglob('*')
                 if p.is_file() and (p.relative_to(source).parts[0] in SOURCE_DIRS
                                    or len(p.relative_to(source).parts) == 1)]
    names = [n for n in names if not any(part in EXCLUDED or part.endswith('.egg-info') for part in n.parts)
             and not n.name.endswith(('.pyc', '.pyo', '.log', '.deb', '.rpm', '.exe', '.tar.gz', '.sha256'))]
    # Preserve the complete examples tree, including ignored configuration/runtime data.
    if (source / 'examples').is_dir():
        names.extend(p.relative_to(source) for p in (source / 'examples').rglob('*'))
    with tarfile.open(destination / (app + '-source.tar.gz'), 'w:gz') as archive:
        for name in sorted(set(names)):
            path = source / name
            if (path.is_file() or path.is_dir()) and not path.is_symlink():
                archive.add(path, arcname=(Path(app + '-source') / name).as_posix(), recursive=False)
    for name in ('SOURCE_REVISIONS.json', 'SOURCE_REVISION.txt', 'TARGET'):
        if (source / name).is_file():
            shutil.copy2(source / name, destination / name)
    return provenance


def _collect(system, app, output, source, patterns, release_date=None):
    for value in (system, app):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', value):
            raise ValueError('Invalid system or application name: ' + value)
    day = release_date or os.environ.get('RELEASE_DATE') or date.today().isoformat()
    date.fromisoformat(day)
    output = Path(os.environ.get('RELEASE_OUTPUT_BASE') or output).resolve()
    source = Path(source).resolve()
    files = []
    for pattern in patterns:
        matches = [Path(p).resolve() for p in glob.glob(str(pattern)) if Path(p).is_file()]
        if not matches:
            raise ValueError('Missing release input: ' + str(pattern))
        files.extend(matches)
    if not files:
        raise ValueError('No build artifacts supplied')
    release = output / (system + '-' + day + '-release')
    release.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.collect-', dir=release) as temporary:
        stage = Path(temporary)
        artifacts = stage / 'artifacts'
        artifacts.mkdir()
        for path in sorted(set(files)):
            target = artifacts / path.name
            if target.exists() and digest(target) != digest(path):
                raise ValueError('Conflicting artifact filenames: ' + path.name)
            shutil.copy2(path, target)
        provenance = source_snapshot(source, stage, app)
        metadata = dict(system=system, application=app, release_date=day,
                        collected_at=datetime.now(timezone.utc).isoformat(),
                        build_platform=platform.platform(), machine=platform.machine(),
                        python=platform.python_version(), source=provenance,
                        artifacts=[p.name for p in sorted(artifacts.iterdir())])
        (stage / 'RELEASE.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
        checksums(stage)
        slot, index = release / app, 1
        while slot.exists():
            index += 1
            slot = release / (app + '-' + str(index))
        stage.rename(slot)
        # TemporaryDirectory tolerates its old path having been moved.
    (release / 'TRANSFER.md').write_text(
        'Copy this entire folder or its sibling .tar.gz archive to Mint.\n'
        'Verify SHA256SUMS before using the files. Each application/build has its own folder.\n'
        'artifacts/ contains native packages, source packages, build recipes and logs supplied by the builder.\n'
        'The source snapshot includes current working files; RELEASE.json records Git provenance when available.\n'
        'When built from Git, source-history.bundle carries HEAD history and its release tags for import on Mint.\n'
        'Preserve all folders when transferring both applications. Repeated builds use numbered application folders.\n'
        'Review native tests, lint results, versions, source changes and release notes on Mint before pushing or publishing.\n'
        'Collection does not commit, push, install, or publish anything.\n', encoding='utf-8')
    checksums(release)
    archive_path = Path(str(release) + '.tar.gz')
    temporary_archive = Path(str(archive_path) + '.tmp')
    with tarfile.open(temporary_archive, 'w:gz') as archive:
        archive.add(release, arcname=release.name)
    temporary_archive.replace(archive_path)
    Path(str(archive_path) + '.sha256').write_text(digest(archive_path) + '  ' + archive_path.name + '\n')
    print('Transfer folder: ' + str(release))
    print('Transfer archive: ' + str(archive_path))
    return release


def collect(system, app, output, source, patterns, release_date=None):
    # Serialize shared-folder updates when the two applications build together.
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', system):
        raise ValueError('Invalid system name: ' + system)
    day = release_date or os.environ.get('RELEASE_DATE') or date.today().isoformat()
    date.fromisoformat(day)
    parent = Path(os.environ.get('RELEASE_OUTPUT_BASE') or output).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    lock = parent / ('.' + system + '-' + day + '-release.lock')
    deadline = time.monotonic() + 120
    while True:
        try:
            lock.mkdir()
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise RuntimeError('Another release collector holds ' + str(lock))
            time.sleep(0.1)
    try:
        return _collect(system, app, output, source, patterns, day)
    finally:
        lock.rmdir()


def native_system():
    if platform.system() == 'Linux':
        try:
            values = {}
            for line in Path('/etc/os-release').read_text().splitlines():
                if '=' in line:
                    key, value = line.split('=', 1)
                    words = shlex.split(value)
                    values[key] = words[0] if words else ''
            name = values.get('ID', 'linux').replace('linuxmint', 'mint')
            return name + values.get('VERSION_ID', '')
        except OSError:
            return 'linux'
    return platform.system().lower()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--system', default=native_system())
    parser.add_argument('--app', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--date', help='Override local build date (YYYY-MM-DD)')
    parser.add_argument('--files', nargs='+', required=True)
    args = parser.parse_args()
    collect(args.system, args.app, args.output, args.source, args.files, args.date)


if __name__ == '__main__':
    main()
