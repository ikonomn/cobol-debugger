import importlib.util
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

GUI_AVAILABLE = importlib.util.find_spec('PyQt5') is not None
if GUI_AVAILABLE:
    from PyQt5.QtCore import QProcess
    from cobgdb_python import frontend


@unittest.skipUnless(GUI_AVAILABLE, 'Optional PyQt5 required')
class FrontendCliTests(unittest.TestCase):
    def test_no_argument_keeps_manual_selection(self):
        app, window = Mock(), Mock()
        app.exec_.return_value = 0
        with patch.object(frontend, 'QApplication', return_value=app), \
                patch.object(frontend, 'Window', return_value=window), \
                patch.object(frontend.QTimer, 'singleShot', side_effect=lambda delay, fn: fn()), \
                patch.object(frontend.QMessageBox, 'information') as notice:
            with self.assertRaises(SystemExit) as status:
                frontend.main([])
        notice.assert_called_once()
        self.assertIs(notice.call_args.args[0], window)
        self.assertIn('-g -fsource-location -ftraceall -O0 -save-temps', notice.call_args.args[2])
        self.assertEqual(status.exception.code, 0)
        window.show.assert_called_once()
        window.load_executable.assert_not_called()
        window.process.started.connect.assert_not_called()

    def test_argument_waits_for_backend_and_preserves_spaces(self):
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / 'my executable'
            source = Path(folder) / 'my source.cbl'
            executable.touch(); source.touch()
            app, window = Mock(), Mock()
            app.exec_.return_value = 0
            window.process.state.return_value = QProcess.Starting
            with patch.object(frontend, 'QApplication', return_value=app), patch.object(frontend, 'Window', return_value=window):
                with self.assertRaises(SystemExit):
                    frontend.main([str(executable), '--source', str(source)])
            callback = window.process.started.connect.call_args[0][0]
            window.load_executable.assert_not_called()
            callback()
            window.load_executable.assert_called_once_with(str(executable), str(source))

    def test_argument_when_backend_is_already_started(self):
        with tempfile.NamedTemporaryFile() as executable:
            app, window = Mock(), Mock()
            app.exec_.return_value = 0
            window.process.state.return_value = QProcess.Running
            with patch.object(frontend, 'QApplication', return_value=app), patch.object(frontend, 'Window', return_value=window), patch.object(frontend.QTimer, 'singleShot', side_effect=lambda delay, fn: fn()):
                with self.assertRaises(SystemExit):
                    frontend.main([executable.name])
            window.load_executable.assert_called_once_with(executable.name, None)

    def test_missing_executable_and_source_without_executable_are_rejected(self):
        for args in (['/missing/compiled/program'], ['--source', '/missing/source.cbl']):
            with self.assertRaises(SystemExit) as status:
                frontend.parse_launch_arguments(args)
            self.assertEqual(status.exception.code, 2)

    def test_project_load_uses_independent_plan_and_does_not_run(self):
        window, plan = Mock(), Mock()
        window.launch_arguments.return_value = {'executable': '/project/bin/main'}
        with patch.object(frontend, 'project_root', return_value='/project'), patch.object(frontend, 'build_plan', return_value=plan):
            frontend.Window.load_executable(window, '/project/bin/main', '/project/src/main.cbl')
        window.launch_arguments.assert_called_once_with('/project/bin/main', plan)
        window.show_source.assert_called_once_with('/project/src/main.cbl')
        window.send.assert_called_once_with('launch', {'executable': '/project/bin/main'})


if __name__ == '__main__':
    unittest.main()
