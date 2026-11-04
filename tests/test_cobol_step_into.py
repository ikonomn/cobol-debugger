"""Real GDB coverage for same-line operations, loops, and subprogram step-into."""
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import time
import unittest
from cobgdb_python.backend import Debugger

@unittest.skipUnless(shutil.which('gdb') and shutil.which('cobc'), 'GDB and cobc required')
class CobolStepIntoTests(unittest.TestCase):
    def test_same_line_loop_and_call(self):
        main='''       identification division.
       program-id. mainprog.
       data division.
       working-storage section.
       01 n pic 9 value 0.
       procedure division.
           move 1 to n add 2 to n
           perform until n > 4
               add 1 to n
           end-perform
           call "subprog"
           display n
           stop run.
'''
        sub='''       identification division.
       program-id. subprog.
       procedure division.
           display "SUBPROGRAM"
           goback.
'''
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/'main.cob';source.write_text(main)
            called=root/'sub.cob';called.write_text(sub)
            exe=root/('main.exe' if __import__('os').name=='nt' else 'main')
            subprocess.run(['cobc','-x','-g','-fsource-location','-ftraceall','-O0','-save-temps',
                '-o',str(exe),str(source),str(called)],cwd=root,check=True,capture_output=True)
            events=queue.Queue();debugger=Debugger(events.put)
            def stop():
                deadline=time.monotonic()+20
                while time.monotonic()<deadline:
                    event=events.get(timeout=max(.01,deadline-time.monotonic()))
                    if event.get('event') in ('stopped','exited'):
                        return event
                self.fail('Missing stop')
            def value():
                return next(v['value'] for v in debugger.cobol_variables()['variables'] if v['name']=='n')
            try:
                debugger.launch({'executable':str(exe)})
                debugger.dispatch('add_breakpoint',{'file':str(source),'line':7})
                debugger.dispatch('run',{});self.assertEqual(stop()['location']['line'],7)
                debugger.dispatch('next',{});self.assertEqual(stop()['location']['line'],7)
                self.assertEqual(value(),'1')
                debugger.dispatch('next',{});self.assertEqual(stop()['location']['line'],8)
                self.assertEqual(value(),'3')
                visits=[]
                for _ in range(18):
                    debugger.dispatch('next',{});event=stop()
                    self.assertEqual(event['event'],'stopped')
                    visits.append(event['location']['line'])
                    if visits[-1]==11:
                        break
                self.assertEqual(visits[-1],11)
                self.assertGreaterEqual(visits.count(9),2)
                debugger.dispatch('step',{});event=stop()
                self.assertEqual(event['location']['file'],str(called))
                self.assertEqual(event['location']['line'],4)
                self.assertFalse(debugger.step_breakpoints)
                debugger.dispatch('add_breakpoint',{'file':str(called),'line':5})
                debugger.dispatch('step',{});event=stop()
                self.assertEqual(event['reason'],'breakpoint-hit')
                self.assertEqual(event['location']['line'],5)
                self.assertFalse(debugger.step_breakpoints)
            finally:
                debugger.close()
