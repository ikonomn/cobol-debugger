import json
import subprocess
import sys
import unittest

class ProtocolTests(unittest.TestCase):
    def test_errors_do_not_break_protocol(self):
        payload = '\n'.join(['[]', '{bad', json.dumps({'id': 1, 'command': 'unknown'}),
                              json.dumps({'id': 2, 'command': 'shutdown'})]) + '\n'
        proc = subprocess.run([sys.executable, '-m', 'cobgdb_python.backend'],
                              input=payload, text=True, capture_output=True, timeout=10)
        records = [json.loads(line) for line in proc.stdout.splitlines()]
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(records[0]['event'], 'ready')
        self.assertEqual([r['ok'] for r in records[1:]], [False, False, False, True])
