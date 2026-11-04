import unittest
from cobgdb_python.backend import Debugger

class StatementStepTests(unittest.TestCase):
    def test_breakpoints_signals_and_unknown_locations_are_not_skipped(self):
        debugger = Debugger(lambda _: None)
        location = {'file': '/source/test.cob', 'line': 7, 'function': 'test_'}
        debugger.next_origin = debugger.location_key(location)
        for reason in ['breakpoint-hit', 'signal-received', 'watchpoint-trigger', 'function-finished']:
            self.assertFalse(debugger.skip_statement_stop({'reason': reason, 'location': location}))
        self.assertFalse(debugger.skip_statement_stop({'reason': 'end-stepping-range', 'location': None}))
        self.assertFalse(debugger.skip_statement_stop({'reason': 'end-stepping-range',
            'location': {**location, 'line': 8}}))

    def test_internal_steps_have_a_limit(self):
        events = []
        debugger = Debugger(events.append)
        location = {'file': '/source/test.cob', 'line': 7, 'function': 'test_'}
        debugger.next_origin = debugger.location_key(location)
        debugger.next_count = 256
        self.assertFalse(debugger.skip_statement_stop({'reason': 'end-stepping-range', 'location': location}))
        self.assertEqual(events[0]['event'], 'diagnostic')

    def test_backwards_program_counter_preserves_loop_iteration(self):
        debugger = Debugger(lambda _: None)
        location = {'file': '/source/test.cob', 'line': 7, 'function': 'test_'}
        debugger.next_origin = debugger.location_key(location)
        debugger.last_step_pc = 0x200
        debugger.last_frame = {'addr': '0x100', 'fullname': location['file'], 'func': 'test_', 'line': '7'}
        self.assertFalse(debugger.skip_statement_stop({'reason': 'end-stepping-range', 'location': location}))

    def test_distinct_statement_on_same_line_is_not_skipped(self):
        debugger = Debugger(lambda _: None)
        location = {'file': '/source/test.cob', 'line': 7, 'function': 'test_'}
        debugger.next_origin = debugger.location_key(location)
        debugger.origin_statement = 'source.c:100'
        debugger.statement_for_frame = lambda *_: {'statement_id': 'source.c:110'}
        self.assertFalse(debugger.skip_statement_stop({'reason': 'end-stepping-range', 'location': location}))

    def test_step_does_not_skip_signal_inside_runtime(self):
        debugger = Debugger(lambda _: None)
        debugger.step_mode = 'step'
        debugger.next_origin = ('/source/test.cob', 7, 'test_')
        debugger.last_frame = {'func': 'cob_display', 'fullname': 'runtime.c'}
        self.assertFalse(debugger.skip_statement_stop({'reason': 'signal-received', 'location': None}))
