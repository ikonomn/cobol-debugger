"""Independent build/debug contract for modern12-compatible project JSON."""
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import unittest
from cobgdb_python.ide_project import build_plan
from cobgdb_python.backend import Debugger


def create_project(root):
    for name in ('src', 'config', 'data', 'copybooks'):
        (root/name).mkdir(parents=True)
    data = {'schema_version': 1, 'name': 'example',
            'defaults': {'enabled': True, 'flags': [], 'copybook_paths': ['copybooks'],
                         'listing': {'enabled': True, 'filename': 'build/{stem}.lst'}},
            'sources': {}, 'debug': {'enabled': True},
            'runtime': {'accepted': True, 'working_directory': '.', 'data_directories': ['data']}}
    (root/'config/project.json').write_text(json.dumps(data))
    source = root/'src/hello.cob'
    source.write_text((Path(__file__).resolve().parents[1]/'examples/hello/hello.cob').read_text())
    return source, data


def compile_plan(plan):
    # Isolated Python ignores site-packages and PYTHONPATH: no IDE or Qt required.
    return subprocess.run([plan.program, '-I', '-S', *plan.arguments], cwd=plan.root,
                          env=plan.environment, capture_output=True, text=True)


@unittest.skipUnless(shutil.which('cobc') and shutil.which('gdb'), 'cobc and GDB required')
class IndependentProjectTests(unittest.TestCase):
    def test_build_discovery_variables_and_accepted_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, _ = create_project(root)
            before = (root/'config/project.json').read_bytes()
            plan = build_plan(source)
            self.assertTrue(plan.arguments[0].endswith('project_build.py'))
            self.assertEqual(plan.missing_debug_flags, [])
            self.assertEqual(plan.runtime_cwd, str(root))
            self.assertEqual(plan.runtime_environment['COB_FILE_PATH'], str(root/'data'))
            built = compile_plan(plan)
            self.assertEqual(built.returncode, 0, built.stdout+built.stderr)
            retained = list((root/'debug_data/src/hello').iterdir())
            self.assertTrue(any(p.suffix == '.c' for p in retained))
            self.assertTrue(all(p.suffix in ('.c', '.h') for p in retained))
            self.assertTrue((root/'build/hello.lst').is_file())
            self.assertFalse(list((root/'build').glob('.compile-*')))
            events = queue.Queue()
            debugger = Debugger(events.put)
            def stopped():
                while True:
                    event = events.get(timeout=20)
                    if event.get('event') == 'stopped': return event
            try:
                result = debugger.launch({'executable': str(plan.output), 'cwd': plan.runtime_cwd,
                                          'environment': plan.runtime_environment})
                self.assertEqual(result['source'], str(source))
                debugger.dispatch('add_breakpoint', {'file': str(source), 'line': 7})
                debugger.dispatch('run', {})
                self.assertEqual(stopped()['location']['line'], 7)
                debugger.dispatch('next', {})
                self.assertEqual(stopped()['location']['line'], 8)
                values = {v['name']:v['value'] for v in debugger.cobol_variables()['variables']}
                self.assertEqual(values['counter'], '2')
            finally:
                debugger.close()
            self.assertEqual((root/'config/project.json').read_bytes(), before)
            # Failed compilation preserves the matching successful binary/metadata.
            old = plan.output.read_bytes()
            headers = {p.name: p.read_bytes() for p in retained}
            source.write_text(source.read_text()+'           INVALID-SYNTAX HERE\n')
            failed = compile_plan(plan)
            self.assertNotEqual(failed.returncode, 0)
            self.assertEqual(plan.output.read_bytes(), old)
            self.assertEqual({p.name:p.read_bytes() for p in retained}, headers)
            self.assertFalse(list((root/'build').glob('.compile-*')))
            (root/'data').rmdir()
            with self.assertRaisesRegex(ValueError, 'missing'):
                build_plan(source)
