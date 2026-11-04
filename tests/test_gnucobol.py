"""Integration test: requires GDB and cobc; skipped when unavailable."""
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import unittest
from cobgdb_python.backend import Debugger

@unittest.skipUnless(shutil.which('gdb') and shutil.which('cobc'), 'GDB and cobc required')
class GnuCOBOLTests(unittest.TestCase):
    def test_breakpoint_step_and_variables(self):
        source = Path(__file__).resolve().parents[1] / 'examples' / 'hello' / 'hello.cob'
        events = queue.Queue()
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder) / ('hello.exe' if __import__('os').name == 'nt' else 'hello')
            subprocess.run(['cobc', '-g', '-fsource-location', '-ftraceall', '-O0', '-x',
                            '-o', str(exe), str(source)], check=True, capture_output=True, cwd=folder)
            debugger = Debugger(events.put)
            def wait_event(name):
                import time
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    event = events.get(timeout=max(.01, deadline-time.monotonic()))
                    if event.get('event') == name:
                        return event
                self.fail('Missing event: ' + name)
            try:
                debugger.dispatch('launch', {'executable': str(exe)})
                result = debugger.dispatch('add_breakpoint', {'file': str(source), 'line': 7})
                self.assertIn('bkpt', result)
                debugger.dispatch('run', {})
                stopped = wait_event('stopped')
                self.assertEqual(stopped['reason'], 'breakpoint-hit')
                self.assertEqual(stopped['location']['line'], 7)
                self.assertTrue(stopped['location']['file'].endswith('hello.cob'))
                debugger.dispatch('next', {})
                event = wait_event('stopped')
                self.assertTrue(event['location']['file'].endswith('hello.cob'))
                self.assertEqual(event['location']['line'], 8)
                values = {v['name']: v['value'] for v in debugger.dispatch('cobol_variables', {})['variables']}
                self.assertEqual(values['counter'], '2')
                self.assertIn('variables', debugger.dispatch('variables', {}))
                debugger.dispatch('continue', {})
                self.assertTrue(wait_event('exited')['reason'].startswith('exited'))
            finally:
                debugger.close()
