"""Stage the distributable examples without local build output."""
import argparse
from pathlib import Path
import shutil


def stage_examples(destination):
    script_dir = Path(__file__).resolve().parent
    source = script_dir.parent / 'examples'
    for entry in (script_dir / 'example-files.txt').read_text(encoding='utf-8').splitlines():
        target = destination / entry
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / entry, target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    stage_examples(parser.parse_args().destination)
