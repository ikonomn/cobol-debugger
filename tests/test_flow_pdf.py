import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

@unittest.skipUnless(importlib.util.find_spec('PyQt5'), 'Optional PyQt5 required')
class FlowPDFTests(unittest.TestCase):
    def test_export_preserves_highlight(self):
        os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
        from PyQt5.QtWidgets import QApplication, QPushButton
        from cobgdb_python.flowchart import FlowchartDialog
        app=QApplication.instance() or QApplication([])
        dialog=FlowchartDialog()
        try:
            dialog.load_source('demo.cob','''       PROCEDURE DIVISION.
           IF N = 1
               DISPLAY N
           ELSE
               ACCEPT N
           END-IF
           GOBACK.
''')
            dialog.highlight(3)
            current=dialog.items[dialog.model.at_line(3).id]
            color=current.brush().color().name()
            self.assertIn('Export PDF',[b.text() for b in dialog.findChildren(QPushButton)])
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'flow.pdf'
                self.assertGreater(dialog.write_pdf(path),1)
                self.assertTrue(path.read_bytes().startswith(b'%PDF'))
                self.assertGreater(path.stat().st_size,1000)
                self.assertEqual(current.brush().color().name(),color)
        finally:dialog.close()
