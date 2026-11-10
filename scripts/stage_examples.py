"""Stage the complete examples tree, including configuration and runtime data."""
import argparse
from pathlib import Path
import shutil


def stage_examples(destination):
    source = Path(__file__).resolve().parents[1] / 'examples'
    shutil.copytree(source, destination, dirs_exist_ok=True, copy_function=shutil.copy2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    stage_examples(parser.parse_args().destination)
