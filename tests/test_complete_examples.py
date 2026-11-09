"""Examples must retain files and empty directories outside the old allowlist."""
from pathlib import Path
import shutil
import subprocess
import sys


def test_complete_example_staging(tmp_path):
    scripts = tmp_path / 'scripts'
    scripts.mkdir()
    source = Path(__file__).resolve().parents[1] / 'scripts/stage_examples.py'
    shutil.copyfile(source, scripts / source.name)
    examples = tmp_path / 'examples'
    for relative in ['worldcities/config/worldcities-sqlite.conf', 'easter/MV_FEASTS2026.TXT',
                     'worldcities/build/database.db', 'hello/bin/hello', '.hidden']:
        file = examples / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(relative)
    (examples / 'empty').mkdir()
    destination = tmp_path / 'staged'
    subprocess.run([sys.executable, str(scripts / source.name), str(destination)], check=True)
    for path in examples.rglob('*'):
        copied = destination / path.relative_to(examples)
        assert copied.exists()
        if path.is_file():
            assert copied.read_bytes() == path.read_bytes()
