import importlib.util
from pathlib import Path
import pytest

def test_writable_examples_preserve_user_files_and_links(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('user_examples', Path(__file__).resolve().parents[1]/'cobgdb_python'/'user_examples.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = tmp_path/'installed'
    (source/'nested').mkdir(parents=True)
    (source/'nested/data.txt').write_text('original')
    (source/'source.cob').write_text('program')
    (source/'link').symlink_to(source/'source.cob')
    home = tmp_path/'home'
    home.mkdir()
    monkeypatch.setattr(Path, 'home', lambda: home)
    dest = module.ensure_user_examples([source], 'Examples')
    assert dest == home/'Examples'
    assert (dest/'nested/data.txt').read_text() == 'original'
    assert not (dest/'link').exists()
    (dest/'nested/data.txt').write_text('edited')
    (source/'new.cob').write_text('new')
    outside = tmp_path/'outside'
    outside.write_text('unchanged')
    (dest/'source.cob').unlink()
    (dest/'source.cob').symlink_to(outside)
    module.ensure_user_examples([source], 'Examples')
    assert (dest/'nested/data.txt').read_text() == 'edited'
    assert (dest/'new.cob').read_text() == 'new'
    assert outside.read_text() == 'unchanged'
    assert module.ensure_user_examples([tmp_path/'missing'], 'Missing') is None
