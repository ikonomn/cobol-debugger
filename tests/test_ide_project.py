from pathlib import Path
import json
import tempfile
import unittest
from cobgdb_python.ide_project import project_root, original_source

class ProjectPathTests(unittest.TestCase):
    def test_generated_and_copybook_map_to_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ['src','build','config','copybooks','bin']:(root/name).mkdir()
            (root/'config/project.json').write_text('{}')
            source=root/'src/main.cbl';source.touch()
            self.assertEqual(project_root(root/'build/main.cbsql'),root)
            self.assertEqual(original_source(root,root/'build/main.cbsql'),source)
            self.assertEqual(original_source(root,root/'copybooks/work.cpy',root/'bin/main'),source)
            (root/'src/main.cob').touch()
            with self.assertRaises(ValueError):original_source(root,root/'build/main.cbsql')

    def test_executable_resolves_flat_gui_project(self):
        from cobgdb_python.ide_project import build_plan

        example = Path(__file__).resolve().parents[1] / 'examples/gui'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'config').mkdir()
            (root / 'bin').mkdir()
            for name in ('config/project.json', 'score.cob', 'score_window.c'):
                (root / name).write_bytes((example / name).read_bytes())

            plan = build_plan(root / 'bin/score')
            self.assertEqual(plan.source, root / 'score.cob')
            self.assertEqual(plan.runtime_cwd, str(root / 'bin'))
            self.assertFalse(plan.module)

    def test_standalone_has_no_project(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertIsNone(project_root(Path(folder)/'hello.cob'))
