"""Keep program interaction in the GUI's embedded console."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest


@unittest.skipUnless(os.name == 'posix' and importlib.util.find_spec('PyQt5') and shutil.which('cobc') and shutil.which('gdb'),
                     'PyQt5, cobc and GDB required')
class EmbeddedConsoleTests(unittest.TestCase):
    def test_program_output_and_input_round_trip(self):
        from PyQt5.QtCore import QProcess
        from PyQt5.QtWidgets import QApplication
        from cobgdb_python.frontend import Window
        app = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'input.cob'
            source.write_text(
                'identification division.\nprogram-id. input-test.\n'
                'data division.\nworking-storage section.\n01 choice pic 9.\n'
                'procedure division.\ndisplay "ENTER CHOICE"\n'
                'accept choice\ndisplay "CHOICE=" choice\ngoback.\n')
            exe = root/'input-test'
            subprocess.run(['cobc', '-free', '-x', '-g', '-fsource-location',
                            '-ftraceall', '-O0', '-save-temps', '-o', str(exe),
                            str(source)], cwd=root, check=True, capture_output=True)
            window = Window()
            def wait_for(predicate):
                deadline = time.monotonic() + 12
                while not predicate():
                    app.processEvents()
                    if time.monotonic() > deadline:
                        self.fail(window.messages.toPlainText() + '\n' +
                                  window.program_output.toPlainText())
                    time.sleep(.01)
            try:
                wait_for(lambda: window.process.state() == QProcess.Running)
                self.assertNotIn('native_terminal', window.launch_arguments(str(exe)))
                window.load_executable(str(exe), str(source))
                wait_for(lambda: window.session_loaded)
                self.assertEqual(window.terminal_mode, 'embedded')
                window.send('run')
                wait_for(lambda: 'ENTER CHOICE' in window.program_output.toPlainText())
                self.assertTrue(window.buttons['input'].isEnabled())
                window.input_text.setText('2')
                window.buttons['input'].click()
                wait_for(lambda: 'CHOICE=2' in window.program_output.toPlainText())
                wait_for(lambda: window.execution_state == 'exited')
            finally:
                window.close()
