import unittest
from cobgdb_python.flow_model import build_flow
from cobgdb_python.flow_routes import route_edges, YES, NO

class RouteTests(unittest.TestCase):
    def test_nested_connections_do_not_share_overlapping_tracks(self):
        model=build_flow('''       PROCEDURE DIVISION.
           IF A = 1
               IF B = 2
                   DISPLAY B
               ELSE
                   ACCEPT B
               END-IF
           ELSE
               MOVE 0 TO B
           END-IF
           DISPLAY B
           GOBACK.
''')
        positions,routes=route_edges(model)
        self.assertTrue(any(r['label']=='Yes' and r['color']==YES for r in routes))
        self.assertTrue(any(r['label']=='No' and r['color']==NO for r in routes))
        self.assertGreaterEqual(positions[1][1]-positions[0][1],200)
        for i,first in enumerate(routes):
            if first['track'] is None:continue
            a,b=sorted((first['points'][0][1],first['points'][-1][1]))
            for second in routes[i+1:]:
                if second['track']!=first['track']:continue
                c,d=sorted((second['points'][0][1],second['points'][-1][1]))
                self.assertTrue(b+25<c or a>d+25)
        for target in {r['target'] for r in routes}:
            ends=[r['points'][-1] for r in routes if r['target']==target]
            self.assertEqual(len(ends),len(set(ends)))
