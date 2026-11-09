"""Include the curated examples in wheel installations on every platform."""
from pathlib import Path
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithExamples(build_py):
    def run(self):
        super().run()
        root = Path(__file__).resolve().parent
        destination = Path(self.build_lib) / 'cobgdb_python/example_templates'
        if destination.exists():
            shutil.rmtree(destination)
        for entry in (root / 'scripts/example-files.txt').read_text().splitlines():
            target = destination / entry
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / 'examples' / entry, target)


setup(cmdclass={'build_py': BuildWithExamples})
