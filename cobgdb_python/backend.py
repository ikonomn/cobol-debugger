"""JSON Lines server. Stdout is reserved exclusively for protocol messages."""
import bisect
import json
import codecs
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from .mi import parse_record
from .source_map import SourceMap
from .source_discovery import choose_source
from .variables import fields_from_c, display_value

class Debugger:
    def __init__(self, emit):
        self.emit = emit
        self.proc = None
        self.pending = {}
        self.token = 0
        self.write_lock = threading.Lock()
        self.step_breakpoints = set()
        self.runtime_finish = False
        self.step_mode = 'next'
        self.origin_statement = None
        self.last_step_pc = None
        self.statement_addresses = []
        self.statement_records = []
        self.next_origin = None
        self.next_count = 0
        self.internal_next = set()
        self.internal_cleanup = set()
        self.last_location = None
        self.deferred_stop = None
        self.source_map = SourceMap()
        self.last_frame = {}
        self.variable_cfiles = {}
        self.terminal = None
        self.output_stop = threading.Event()

    def read_program(self, fd):
        import select
        decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        while not self.output_stop.is_set():
            try:
                readable, _, _ = select.select([fd], [], [], 0.1)
                if not readable:
                    continue
                chunk = os.read(fd, 4096)
                if not chunk:
                    break
                text = decoder.decode(chunk)
                if text:
                    self.emit({'event': 'output', 'channel': 'program', 'text': text})
            except OSError:
                break
        tail = decoder.decode(b'', final=True)
        if tail:
            self.emit({'event': 'output', 'channel': 'program', 'text': tail})

    def read(self, proc):
        try:
            for line in proc.stdout:
                try:
                    record = parse_record(line)
                except (ValueError, SyntaxError, IndexError) as exc:
                    self.emit({'event': 'diagnostic', 'message': str(exc), 'raw': line.rstrip()})
                    continue
                if not record:
                    continue
                if record['kind'] == '^':
                    if record['token'] in self.internal_cleanup:
                        self.internal_cleanup.discard(record['token'])
                        continue
                    if record['token'] in self.internal_next:
                        self.internal_next.discard(record['token'])
                        if record['cls'] == 'error':
                            self.next_origin = None
                            self.emit({'event': 'diagnostic', 'message': record['data'].get('msg', 'Automatic Next failed')})
                            if self.deferred_stop:
                                self.last_location = self.deferred_stop.get('location')
                                self.emit(self.deferred_stop)
                                self.deferred_stop = None
                        continue
                    waiter = self.pending.get(record['token'])
                    if waiter:
                        waiter.put(record)
                elif record['kind'] == '*':
                    data = record['data']
                    event = {'event': record['cls'], **data}
                    frame = data.get('frame', {})
                    if record['cls'] == 'stopped':
                        self.last_frame = frame.copy()
                    if frame:
                        event['location'] = {'file': frame.get('fullname', frame.get('file')),
                                             'line': int(frame.get('line', 0)),
                                             'function': frame.get('func')}
                    if event.get('location', {}).get('file'):
                        raw = event['location'].copy()
                        mapped = self.source_map.location(raw['file'], raw['line'])
                        if mapped:
                            event['generated_location'] = raw
                            event['location'] = {**raw, **mapped}
                            event['frame'] = {**frame, 'file': mapped['file'],
                                              'fullname': mapped['file'], 'line': str(mapped['line'])}
                        elif str(raw['file']).lower().endswith('.c'):
                            event['generated_location'] = raw
                            event['location'] = None
                            event['source_mapping'] = 'unavailable'
                    if data.get('reason', '').startswith('exited'):
                        event['event'] = 'exited'
                    if record['cls'] == 'stopped':
                        if str(event.get('bkptno', '')) in self.step_breakpoints:
                            event['reason'] = 'end-stepping-range'
                            event['step_into_entry'] = True
                            self.step_breakpoints.discard(str(event['bkptno']))
                        if not event.get('step_into_entry') and self.skip_statement_stop(event):
                            continue
                        self.clear_step_breakpoints()
                        self.next_origin = None
                        self.deferred_stop = None
                        self.last_location = event.get('location')
                    self.emit(event)
                elif record['kind'] in '~@&' or record['kind'] == 'output':
                    self.emit({'event': 'output', 'channel': record['kind'], 'text': record['text']})
                elif record['kind'] == '=':
                    self.emit({'event': 'notification', 'name': record['cls'], 'data': record['data']})
        finally:
            for waiter in list(self.pending.values()):
                waiter.put({'cls': 'error', 'data': {'msg': 'GDB disconnected'}})
            self.emit({'event': 'backend_gdb_exited', 'code': proc.wait()})

    def clear_step_breakpoints(self):
        numbers = self.step_breakpoints.copy()
        self.step_breakpoints.clear()
        if not numbers or not self.proc or self.proc.poll() is not None:
            return
        with self.write_lock:
            self.token += 1
            self.internal_cleanup.add(self.token)
            self.proc.stdin.write(f"{self.token}-break-delete {' '.join(sorted(numbers))}\n")
            self.proc.stdin.flush()

    def prepare_statement_addresses(self):
        """Query line tables on the command thread; the reader never blocks on GDB."""
        self.statement_addresses = []
        self.statement_records = []
        filename = self.last_frame.get('fullname', self.last_frame.get('file', ''))
        files = self.command('-file-list-exec-source-files').get('files', [])
        candidates = [Path(f.get('fullname', f.get('file', ''))) for f in files]
        cached = self.variable_cfiles.get(self.last_frame.get('func', ''))
        candidates = [cached] if cached and self.step_mode == 'next' else list(dict.fromkeys(p for p in candidates if p.suffix.lower() == '.c' and p.exists()))
        records = []
        self.step_entries = []
        for cfile in candidates:
            if not cfile:
                continue
            if self.step_mode == 'step':
                import re
                text = cfile.read_text(encoding='utf-8', errors='replace')
                current_function = re.sub(r'[^a-z0-9]', '', self.last_frame.get('func', '').lower())
                for match in re.finditer(r'/\*\s*Line:\s*(\d+)\s*:\s*Entry\s+([^:]+):\s*(.*?)\s*\*/', text):
                    line, name, source = match.groups()
                    if re.sub(r'[^a-z0-9]', '', name.lower()) != current_function:
                        entry_source = Path(source.strip())
                        if not entry_source.is_absolute():
                            entry_source = cfile.parent / entry_source
                        self.step_entries.append((str(entry_source.resolve()), int(line)))
            try:
                lines = self.command('-symbol-list-lines ' + json.dumps(str(cfile))).get('lines', [])
            except RuntimeError:
                continue
            for record in lines:
                detail = self.source_map.statement(cfile, int(record['line']))
                if detail:
                    records.append((int(record['pc'], 16), detail))
        records.sort(key=lambda item: item[0])
        self.statement_addresses = [pc for pc, _ in records]
        self.statement_records = [detail for _, detail in records]

    def statement_for_frame(self, frame, location):
        if not location:
            return None
        filename = frame.get('fullname', frame.get('file', ''))
        if filename.endswith('.c'):
            return self.source_map.statement(filename, int(frame.get('line', 0)))
        try:
            pc = int(frame.get('addr', ''), 16)
        except ValueError:
            return None
        # A #line COBOL stop precedes its generated C statement body.
        index = bisect.bisect_left(self.statement_addresses, pc)
        if index < len(self.statement_records):
            detail = self.statement_records[index]
            if self.location_key({**detail, 'function': location.get('function')}) == self.location_key(location):
                return detail
        return None

    def skip_statement_stop(self, event):
        """Continue only ordinary step completions; preserve all external stops."""
        if self.next_origin is None or event.get('reason') not in ('end-stepping-range', 'function-finished'):
            return False
        if event.get('reason') == 'function-finished' and not self.runtime_finish:
            return False
        self.runtime_finish = False
        location = event.get('location')
        frame = self.last_frame or event.get('frame', {})
        filename = frame.get('fullname', frame.get('file', '')) or ''
        cobol = bool(location and Path(location.get('file', '')).suffix.lower() in ('.cob', '.cbl', '.cbsql', '.cpy'))
        runtime = (not cobol and self.step_mode == 'step' and
                   (frame.get('func') or '').startswith(('cob_', 'cob_sys_', '__', 'memcpy', 'memset', 'strlen')))
        generated_setup = (not cobol and self.step_mode == 'step' and
                           str(Path(filename)) in self.source_map.cache)
        command = '-exec-finish' if runtime else '-exec-next' if generated_setup else '-exec-step' if self.step_mode == 'step' else '-exec-next'
        if not runtime and not generated_setup:
            if not cobol or self.location_key(location) != self.next_origin:
                return False
            detail = self.statement_for_frame(frame, location)
            if detail and self.origin_statement and detail['statement_id'] != self.origin_statement:
                return False
            try:
                pc = int(frame.get('addr', ''), 16)
            except ValueError:
                pc = None
            # A backwards/repeated PC is a new visit, not more setup for one statement.
            if pc is not None and self.last_step_pc is not None and pc <= self.last_step_pc:
                return False
            if pc is not None:
                self.last_step_pc = pc
        if self.next_count >= 256:
            self.emit({'event': 'diagnostic', 'message': 'COBOL stepping reached its 256 internal-step limit; paused safely'})
            return False
        self.next_count += 1
        self.runtime_finish = command == '-exec-finish'
        self.deferred_stop = event
        try:
            with self.write_lock:
                if self.next_origin is None:
                    return False
                self.token += 1
                token = self.token
                self.internal_next.add(token)
                self.proc.stdin.write(f'{token}{command}\n')
                self.proc.stdin.flush()
        except OSError as exc:
            self.internal_next.discard(token)
            self.emit({'event': 'diagnostic', 'message': str(exc)})
            return False
        return True

    @staticmethod
    def location_key(location):
        filename = os.path.normcase(os.path.normpath(location.get('file', '')))
        return filename, location.get('line'), location.get('function')

    def command(self, command, timeout=10):
        if not self.proc or self.proc.poll() is not None:
            raise RuntimeError('Launch a debugger session first')
        waiter = queue.Queue()
        with self.write_lock:
            self.token += 1
            token = self.token
            self.pending[token] = waiter
            try:
                self.proc.stdin.write(f'{token}{command}\n')
                self.proc.stdin.flush()
            except Exception:
                self.pending.pop(token, None)
                raise
        try:
            try:
                result = waiter.get(timeout=timeout)
            except queue.Empty:
                raise RuntimeError('GDB response timed out; session state may be uncertain')
            if result['cls'] == 'error':
                raise RuntimeError(result['data'].get('msg', 'GDB error'))
            return result['data']
        finally:
            self.pending.pop(token, None)

    def close(self):
        self.step_breakpoints.clear()
        self.variable_cfiles.clear()
        self.next_origin = None
        self.last_location = None
        self.deferred_stop = None
        if self.proc:
            if self.proc.poll() is None:
                try:
                    self.command('-gdb-exit', timeout=2)
                except (RuntimeError, OSError):
                    pass
                try:
                    self.proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait()
            self.reader.join(timeout=2)
            self.proc.stdin.close()
            self.proc.stdout.close()
            self.proc = None
        if self.terminal:
            self.output_stop.set()
            self.output_reader.join(timeout=1)
            for fd in self.terminal:
                os.close(fd)
            self.terminal = None

    def launch(self, args):
        if self.proc:
            raise ValueError('A session already exists; shutdown before launching another')
        executable = Path(args['executable']).expanduser().resolve(strict=True)
        if executable.suffix.lower() in ('.cbl', '.cob', '.cbsql'):
            raise ValueError('Select the compiled executable with Executable; open .cbl/.cob/.cbsql files with Source')
        cwd = Path(args.get('cwd', executable.parent)).expanduser().resolve(strict=True)
        options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
        environment = args.get('environment', {})
        if not isinstance(environment, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in environment.items()):
            raise ValueError('environment must contain string names and values')
        self.proc = subprocess.Popen([args.get('gdb', 'gdb'), '-nx', '--quiet', '--interpreter=mi2'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=cwd, env={**os.environ, **environment}, text=True, encoding='utf-8', errors='replace', bufsize=1, **options)
        self.reader = threading.Thread(target=self.read, args=(self.proc,), daemon=True)
        self.reader.start()
        terminal_mode = 'embedded' if os.name == 'posix' else 'unavailable'
        tty = args.get('tty')
        try:
            self.command('-gdb-set pagination off')
            self.command('-gdb-set mi-async on')
            self.command('-file-exec-and-symbols ' + json.dumps(str(executable)))
            if os.name == 'nt':
                self.command('-gdb-set new-console off')
            if os.name == 'posix' and not tty:
                import pty
                master, slave = pty.openpty()
                self.terminal = (master, slave)
                self.output_stop.clear()
                self.output_reader = threading.Thread(target=self.read_program, args=(master,), daemon=True)
                self.output_reader.start()
                self.command('-inferior-tty-set ' + json.dumps(os.ttyname(slave)))
            if tty:
                self.command('-inferior-tty-set ' + json.dumps(tty))
                terminal_mode = 'native'
            if args.get('arguments'):
                self.command('-exec-arguments ' + ' '.join(json.dumps(a) for a in args['arguments']))
        except Exception:
            self.close()
            raise
        result = {'executable': str(executable), 'platform': sys.platform,
                  'terminal_mode': terminal_mode}
        try:
            files = self.command('-file-list-exec-source-files').get('files', [])
            source, candidates = choose_source(files, executable, cwd)
            result.update(source=source, sources=candidates)
            if source is None:
                result['source_notice'] = ('Multiple COBOL sources match; select Source manually'
                    if candidates else 'No accessible COBOL source found in debug information; select Source manually')
        except RuntimeError as exc:
            result['source_notice'] = 'Source discovery failed: ' + str(exc)
        return result

    def cobol_variables(self):
        frame = self.last_frame
        filename = frame.get('fullname', frame.get('file', ''))
        if not filename:
            raise RuntimeError('Pause at a COBOL statement first')
        function = frame.get('func', '')
        cfile = Path(filename)
        if cfile.suffix.lower() != '.c' or not cfile.exists():
            cached = self.variable_cfiles.get(function)
            if cached and cached.exists():
                cfile = cached
            else:
                files = self.command('-file-list-exec-source-files').get('files', [])
                candidates = list(dict.fromkeys(Path(f.get('fullname', f.get('file', ''))) for f in files))
                candidates = [p for p in candidates if p.suffix.lower() == '.c' and p.exists()]
                cfile = next((p for p in candidates if p.stem.casefold() == Path(filename).stem.casefold()), None)
                if cfile is None:
                    # A first stop can be inside a COPY member. Match the source
                    # referenced by generated line metadata, never an arbitrary C file.
                    matches = []
                    target = os.path.normcase(os.path.normpath(filename))
                    for candidate in candidates:
                        try:
                            text = candidate.read_text(encoding='utf-8', errors='replace')
                        except OSError:
                            continue
                        import re
                        refs = re.findall(r'^\s*#\s*(?:line\s+)?\d+\s+"([^"\n]+)"', text, re.M)
                        if any(os.path.normcase(os.path.normpath(ref)) == target for ref in refs):
                            matches.append(candidate)
                    if len(matches) == 1:
                        cfile = matches[0]
        if cfile is None:
            raise RuntimeError('Generated C metadata unavailable for this program/copybook; retain matching debug build files')
        self.variable_cfiles[function] = cfile
        rows = []
        for field in fields_from_c(cfile):
            row = {'name': field['name'], 'value': '', 'format': '', 'size': field['size']}
            try:
                if field['size'] > 65536:
                    raise RuntimeError('Field too large for automatic display')
                memory = self.command('-data-read-memory-bytes ' +
                    field['symbol'] + '.data ' + str(field['size']))
                raw = bytes.fromhex(''.join(m['contents'] for m in memory.get('memory', [])))
                row['value'], row['format'] = display_value(raw, field['attribute'])
            except RuntimeError as exc:
                row['value'] = '<unavailable>'
                row['error'] = str(exc)
            rows.append(row)
        return {'variables': rows}

    def dispatch(self, op, args):
        if op == 'cobol_variables':
            return self.cobol_variables()
        if op == 'input':
            if not self.terminal:
                raise RuntimeError('Program input requires the managed Linux terminal; Windows input is not implemented yet')
            data = args['text'].encode('utf-8')
            if args.get('newline', True):
                data += b'\n'
            written = 0
            while written < len(data):
                written += os.write(self.terminal[0], data[written:])
            return {'bytes_written': written}
        if op == 'launch':
            return self.launch(args)
        commands = {'run': '-exec-run', 'continue': '-exec-continue', 'next': '-exec-next',
                    'step': '-exec-step', 'finish': '-exec-finish', 'pause': '-exec-interrupt',
                    'stack': '-stack-list-frames', 'variables': '-stack-list-variables --all-values'}
        if op in commands:
            if op in ('next', 'step'):
                self.step_mode = op
                self.runtime_finish = False
                try:
                    self.prepare_statement_addresses()
                except RuntimeError:
                    self.statement_addresses, self.statement_records = [], []
                if op == 'step':
                    for source, line in dict.fromkeys(getattr(self, 'step_entries', [])):
                        try:
                            result = self.command('-break-insert -t ' + json.dumps(f'{source}:{line}'))
                            self.step_breakpoints.add(str(result['bkpt']['number']))
                        except RuntimeError:
                            continue
                detail = self.statement_for_frame(self.last_frame, self.last_location)
                self.origin_statement = detail['statement_id'] if detail else None
                try:
                    self.last_step_pc = int(self.last_frame.get('addr', ''), 16)
                except ValueError:
                    self.last_step_pc = None
                self.next_origin = self.location_key(self.last_location) if self.last_location else None
                self.next_count = 0
            elif op in ('run', 'continue', 'finish', 'pause'):
                self.next_origin = None
                self.clear_step_breakpoints()
            try:
                return self.command(commands[op])
            except Exception:
                if op in ('next', 'step'):
                    self.next_origin = None
                    self.clear_step_breakpoints()
                raise
        if op == 'add_breakpoint':
            line = int(args['line'])
            if line < 1:
                raise ValueError('Line must be positive')
            return self.command('-break-insert -f ' + json.dumps(f"{args['file']}:{line}"))
        if op == 'remove_breakpoint':
            return self.command('-break-delete ' + str(int(args['number'])))
        if op == 'evaluate':
            return self.command('-data-evaluate-expression ' + json.dumps(args['expression']))
        if op in ('reset', 'shutdown'):
            self.close()
            return {}
        raise ValueError(f'Unknown command: {op}')

def main():
    output_lock = threading.Lock()
    def emit(message):
        with output_lock:
            print(json.dumps(message, ensure_ascii=True), flush=True)
    debugger = Debugger(emit)
    emit({'event': 'ready', 'protocol_version': 1})
    try:
        for line in sys.stdin:
            request = None
            try:
                request = json.loads(line)
                if not isinstance(request, dict):
                    raise ValueError('Request must be a JSON object')
                result = debugger.dispatch(request['command'], request.get('arguments', {}))
                emit({'id': request.get('id'), 'ok': True, 'result': result})
                if request['command'] == 'shutdown':
                    break
            except Exception as exc:
                emit({'id': request.get('id') if isinstance(request, dict) else None,
                      'ok': False, 'error': str(exc)})
    finally:
        debugger.close()

if __name__ == '__main__':
    main()
