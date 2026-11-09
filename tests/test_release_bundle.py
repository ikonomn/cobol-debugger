import importlib.util
import json
from pathlib import Path
import subprocess
import tarfile
import pytest

spec = importlib.util.spec_from_file_location('release_bundle', Path(__file__).resolve().parents[1]/'scripts/release_bundle.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_transfer_collects_current_source_and_preserves_rebuilds(tmp_path):
    source = tmp_path/'repo'
    source.mkdir()
    subprocess.run(['git','init',str(source)], check=True, capture_output=True)
    def git(*args):
        return subprocess.run(['git','-C',str(source),*args],check=True,capture_output=True)
    (source/'README.md').write_text('committed')
    git('add','README.md')
    git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','baseline')
    (source/'README.md').write_text('working changes')
    (source/'new_module.py').write_text('print(1)')
    (source/'.git/info/exclude').write_text('.local-guidance/\n')
    (source/'.local-guidance').mkdir()
    (source/'.local-guidance/private.md').write_text('private')
    package = tmp_path/'package.deb'
    package.write_bytes(b'test artifact')
    release = m.collect('mint21.1','ide',tmp_path/'out',source,[package], '2026-11-07')
    assert release.name=='mint21.1-2026-11-07-release'
    metadata=json.loads((release/'ide/RELEASE.json').read_text())
    assert metadata['source']['dirty'] is True
    assert metadata['source']['revision']
    git('bundle','verify',str(release/'ide/source-history.bundle'))
    with tarfile.open(release/'ide/ide-source.tar.gz') as archive:
        assert archive.extractfile('ide-source/README.md').read()==b'working changes'
        assert archive.extractfile('ide-source/new_module.py').read()==b'print(1)'
        assert not any('private' in n for n in archive.getnames())
    package.write_bytes(b'new build')
    m.collect('mint21.1','ide',tmp_path/'out',source,[package], '2026-11-07')
    assert (release/'ide/artifacts/package.deb').read_bytes()==b'test artifact'
    assert (release/'ide-2/artifacts/package.deb').read_bytes()==b'new build'
    subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=release,check=True,capture_output=True)
    with tarfile.open(str(release)+'.tar.gz') as archive:
        assert any('/ide-2/' in n for n in archive.getnames())


def test_missing_or_conflicting_inputs_do_not_create_completed_build(tmp_path):
    with pytest.raises(ValueError,match='Missing release input'):
        m.collect('windows11-x64','debugger',tmp_path/'out',tmp_path,[tmp_path/'missing.exe'])
    first=tmp_path/'one'; second=tmp_path/'two'
    first.mkdir();second.mkdir()
    (first/'same.exe').write_bytes(b'1');(second/'same.exe').write_bytes(b'2')
    with pytest.raises(ValueError,match='Conflicting artifact'):
        m.collect('windows11-x64','debugger',tmp_path/'out',tmp_path,[first/'same.exe',second/'same.exe'])
    assert not any((tmp_path/'out').glob('*/debugger'))


def test_source_export_without_git_and_windows_patterns(tmp_path):
    source=tmp_path/'source';source.mkdir()
    (source/'scripts').mkdir();(source/'scripts/build.ps1').write_text('build')
    (source/'dist').mkdir();(source/'dist/private.log').write_text('skip')
    exe=tmp_path/'app.exe';exe.write_bytes(b'exe')
    setup=tmp_path/'app-setup.exe';setup.write_bytes(b'installer')
    release=m.collect('windows11-x64','debugger',tmp_path/'out',source,[str(tmp_path/'*.exe')], '2026-11-07')
    with tarfile.open(release/'debugger/debugger-source.tar.gz') as archive:
        assert archive.getnames()==['debugger-source/scripts/build.ps1']
    assert len(list((release/'debugger/artifacts').glob('*.exe')))==2


def test_parallel_application_builds_share_a_complete_transfer(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    source = tmp_path/'source'
    source.mkdir()
    (source/'README.md').write_text('source')
    artifact=tmp_path/'package.deb'
    artifact.write_bytes(b'package')
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(m.collect, 'mint', app, tmp_path/'output', source,
                             [artifact], '2026-11-07') for app in ('ide','debugger')]
        release=futures[0].result()
        assert futures[1].result()==release
    subprocess.run(['sha256sum','-c','SHA256SUMS'],cwd=release,check=True,capture_output=True)
    with tarfile.open(str(release)+'.tar.gz') as archive:
        names=archive.getnames()
        assert any('/ide/' in n for n in names)
        assert any('/debugger/' in n for n in names)
        assert not any('.collect-' in n for n in names)
