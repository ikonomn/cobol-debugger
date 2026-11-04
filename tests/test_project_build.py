import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from cobgdb_python.ide_project import build_plan, load_config, effective_options
from cobgdb_python.project_source import inspect_source
from test_modern12_adapter import create_project, compile_plan


class ProjectBuildTests(unittest.TestCase):
    def test_overrides_paths_and_no_ide_imports(self):
        with tempfile.TemporaryDirectory(prefix='project space ') as folder:
            root = Path(folder)
            source, data = create_project(root)
            data['defaults'].update(flags=['-Wall', '-I', 'copybooks'],
                environment={'compiler_path': 'tools/cobc', 'path_mode': 'prepend', 'path': 'tools', 'cob_copy_dir': 'copybooks'})
            data['sources']['src/hello.cob'] = {'flags': ['-O1'], 'listing': {'enabled': False},
                                              'environment': {'gixpp_path': 'tools/gixpp'}}
            (root/'config/project.json').write_text(json.dumps(data))
            import builtins
            original = builtins.__import__
            def no_ide(name, *args, **kwargs):
                if name.startswith(('open_cobol_ide', 'pyqode', 'PyQt')):
                    raise AssertionError('Unexpected IDE/Qt dependency: '+name)
                return original(name, *args, **kwargs)
            with patch('builtins.__import__', side_effect=no_ide):
                plan = build_plan(source)
            self.assertEqual(plan.compiler, str(root/'tools/cobc'))
            self.assertEqual(plan.environment['GIXPP'], str(root/'tools/gixpp'))
            self.assertTrue(plan.environment['PATH'].startswith(str(root/'tools')+os.pathsep))
            self.assertIn('-O1', plan.flags)
            self.assertNotIn('-Wall', plan.flags)
            self.assertNotIn('-T', plan.flags)
            self.assertIn(str(root/'copybooks'), plan.flags)

    def test_inheritance_disabled_defaults_and_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, data = create_project(root)
            data['defaults']['flags'] = ['-Wall']
            data['sources']['src/hello.cob'] = {'flags': None}
            self.assertEqual(effective_options(data, 'src/hello.cob')['flags'], ['-Wall'])
            data['defaults']['enabled'] = False
            self.assertIsNone(effective_options(data, 'src/hello.cob').get('flags'))
            for change in ({'schema_version': 9}, {'runtime': {'accepted': True, 'data_directories': 'bad'}},
                           {'debug': {'enabled': 'yes'}}, {'sources': {'../x': {}}}):
                (root/'config/project.json').write_text(json.dumps({**data, **change}))
                with self.assertRaises(ValueError): load_config(root)

    def test_sql_copy_detection_and_module_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, data = create_project(root)
            source.write_text('       identification division.\n       program-id. hello.\n'
                              '       procedure division using item.\n'
                              '      * EXEC SQL comment END-EXEC\n'
                              '           display "EXEC SQL literal"\n'
                              '           copy "query.cpy".\n           goback.\n')
            (root/'copybooks/query.cpy').write_text('           EXEC SQL SELECT 1 END-EXEC.\n')
            plan = build_plan(source)
            self.assertTrue(plan.sql)
            self.assertTrue(plan.module)
            (root/'copybooks/query.cpy').write_text('           display "no SQL".\n')
            self.assertFalse(build_plan(source).sql)
            (root/'copybooks/query.cpy').unlink()
            with self.assertRaisesRegex(ValueError, 'Cannot inspect COPY'): build_plan(source)

    @unittest.skipUnless(shutil.which('cobc'), 'cobc required')
    def test_module_and_release_build(self):
        with tempfile.TemporaryDirectory(prefix='project space ') as folder:
            root = Path(folder)
            source, data = create_project(root)
            source.write_text('       identification division.\n       program-id. hello.\n'
                '       data division.\n       linkage section.\n       01 item pic 9.\n'
                '       procedure division using item.\n           goback.\n')
            data['debug']['enabled'] = False
            data['defaults']['listing']['enabled'] = False
            (root/'config/project.json').write_text(json.dumps(data))
            plan = build_plan(source)
            built = compile_plan(plan)
            self.assertEqual(built.returncode, 0, built.stdout+built.stderr)
            self.assertTrue(plan.output.is_file())
            self.assertFalse((root/'debug_data').exists())
            self.assertFalse((root/'build/hello.lst').exists())
            self.assertIn('-g', plan.missing_debug_flags)

    @unittest.skipUnless(shutil.which('gixpp') and shutil.which('cobc') and Path('/usr/share/gixsql/copy').is_dir(), 'GixSQL and cobc required')
    def test_real_gixsql_build_without_ide(self):
        with tempfile.TemporaryDirectory(prefix='sql project ') as folder:
            root = Path(folder)
            source, data = create_project(root)
            example = Path(__file__).resolve().parents[1]/'examples/worldcities'
            for directory in ('src', 'copybooks'):
                shutil.copytree(example/directory, root/directory, dirs_exist_ok=True)
            source.unlink()
            before = (root/'config/project.json').read_bytes()
            for name in ('sql-error-handler', 'select-greek-cities'):
                plan = build_plan(root/'src'/(name+'.cbl'))
                built = compile_plan(plan)
                self.assertEqual(built.returncode, 0, built.stdout+built.stderr)
                self.assertTrue(plan.output.is_file())
                retained = list((root/'debug_data/src'/name).iterdir())
                self.assertTrue(any(p.suffix == '.c' for p in retained))
                self.assertTrue(all(p.suffix in ('.c', '.h') for p in retained))
            self.assertTrue((root/'build/select-greek-cities.cbsql').is_file())
            self.assertEqual((root/'config/project.json').read_bytes(), before)
