import importlib.util
import os
import unittest

@unittest.skipUnless(importlib.util.find_spec('PyQt5'), 'Optional PyQt5 required')
class ScreenLayoutTests(unittest.TestCase):
    def test_toolbar_wraps_and_window_fits(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PyQt5.QtWidgets import QApplication
        from cobgdb_python.frontend import Window
        app=QApplication.instance() or QApplication([])
        window=Window();window.show()
        try:
            for width in (600,780,1000):
                window.resize(width,550)
                app.processEvents()
                window.fit_screen()
                app.processEvents()
                available=window.screen().availableGeometry()
                self.assertLessEqual(window.frameGeometry().width(),available.width())
                self.assertLessEqual(window.frameGeometry().height(),available.height())
                for button in window.toolbar.buttons:
                    self.assertLess(button.geometry().right(),window.toolbar.width())
                if window.width()<=600:
                    self.assertGreater(len({b.y() for b in window.toolbar.buttons}),1)
        finally:window.close()
