from pathlib import Path
import tempfile
import unittest
from cobgdb_python.source_discovery import choose_source

class DiscoveryTests(unittest.TestCase):
    def test_main_generated_source_and_debug_suffix(self):
        with tempfile.TemporaryDirectory() as folder:
            files=[]
            for name in ['main.cbsql','helper.cbl','copy.cpy']:
                path=Path(folder)/name;path.touch();files.append({'fullname':str(path)})
            source,candidates=choose_source(files,Path(folder)/'main-debug',folder)
            self.assertEqual(Path(source).name,'main.cbsql')
            self.assertEqual(len(candidates),2)

    def test_ambiguous_and_missing_sources(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ['one.cbl','two.cob']:(Path(folder)/name).touch()
            files=[{'file':'one.cbl'},{'file':'two.cob'},{'file':'missing.cbl'}]
            source,candidates=choose_source(files,'program',folder)
            self.assertIsNone(source)
            self.assertEqual(len(candidates),2)
            self.assertEqual(choose_source(files[:1],'program',folder)[0],str(Path(folder)/'one.cbl'))
