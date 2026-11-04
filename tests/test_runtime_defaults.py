import tempfile
from pathlib import Path
import unittest
from cobgdb_python.ide_project import project_runtime


class RuntimeDefaultsTests(unittest.TestCase):
    def test_default_bin_and_explicit_overrides(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'bin').mkdir()
            for runtime, expected in (({}, 'bin'),
                    ({'accepted': False, 'working_directory': '.'}, 'bin'),
                    ({'accepted': True}, 'bin'),
                    ({'accepted': True, 'working_directory': '.'}, '.')):
                with self.subTest(runtime=runtime):
                    data = {'runtime': runtime}
                    cwd, env = project_runtime(root, '/global/fallback', {'KEEP': 'value'}, data)
                    self.assertEqual(cwd, str((root/expected).resolve()))
                    self.assertEqual(env, {'KEEP': 'value'})

    def test_default_can_be_resolved_before_first_build(self):
        with tempfile.TemporaryDirectory() as folder:
            cwd, env = project_runtime(folder, '/fallback', {}, {})
            self.assertEqual(cwd, str(Path(folder)/'bin'))
            self.assertFalse(Path(cwd).exists())
