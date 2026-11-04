"""Timestamped JSON Lines session logs, flushed after every record."""
from datetime import datetime
from pathlib import Path
import json
import os
import uuid

def default_log_directory():
    repository = Path(__file__).resolve().parent.parent
    if (repository/'pyproject.toml').is_file():
        return repository/'logs'
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA', str(Path.home()/'AppData/Local')))
    else:
        base = Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state')))
        if not base.is_absolute():
            base = Path.home()/'.local/state'
    return base/'cobgdb-python'/'logs'


class SessionLog:
    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().astimezone().strftime('%Y%m%d-%H%M%S')
        self.path = directory / f'debug-{stamp}-{uuid.uuid4().hex[:8]}.jsonl'
        self.file = self.path.open('x', encoding='utf-8')
        self.write('session_started', {})

    def write(self, kind, data):
        if self.file.closed:
            return
        entry = {'timestamp': datetime.now().astimezone().isoformat(timespec='milliseconds'),
                 'kind': kind, 'data': data}
        self.file.write(json.dumps(entry, ensure_ascii=True) + '\n')
        self.file.flush()

    def close(self):
        if not self.file.closed:
            self.write('session_ended', {})
            self.file.close()
