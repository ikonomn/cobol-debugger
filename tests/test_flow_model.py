import unittest
from cobgdb_python.flow_model import build_flow

class FlowTests(unittest.TestCase):
    def test_if_else_paths_merge(self):
        model = build_flow('''       PROCEDURE DIVISION.
           IF A = 1
               MOVE 2 TO B
           ELSE
               ACCEPT B
           END-IF
           DISPLAY B
           GOBACK.
''')
        by_line={n.line:n.id for n in model.nodes if n.line}
        edges=set(model.edges)
        self.assertIn((by_line[2],by_line[3],'Yes'),edges)
        self.assertIn((by_line[2],by_line[5],'No'),edges)
        self.assertIn((by_line[3],by_line[7],''),edges)
        self.assertIn((by_line[5],by_line[7],''),edges)
        self.assertNotIn((by_line[3],by_line[5],''),edges)
        self.assertEqual(model.at_line(5).kind,'io')

    def test_unsupported_control_flow_is_reported(self):
        model=build_flow('       PROCEDURE DIVISION.\n           PERFORM WORK UNTIL A = 2\n           GOBACK.\n')
        self.assertTrue(model.warnings)

    def test_nested_if_and_no_else(self):
        model=build_flow('''       PROCEDURE DIVISION.
           IF A = 1
               IF B = 2
                   DISPLAY B
               END-IF
           END-IF
           GOBACK.
''')
        self.assertFalse(model.warnings)
        by_line={n.line:n.id for n in model.nodes if n.line}
        self.assertIn((by_line[2],by_line[7],'No'),model.edges)
