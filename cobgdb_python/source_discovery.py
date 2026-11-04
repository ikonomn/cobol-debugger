"""Choose a main COBOL source only when debug metadata gives a clear match."""
from pathlib import Path

def choose_source(files, executable, cwd):
    sources = []
    for record in files:
        name = record.get('fullname') or record.get('file')
        if not name:
            continue
        path = Path(name)
        if not path.is_absolute():
            path = Path(cwd) / path
        if path.suffix.lower() not in ('.cob', '.cbl', '.cbsql'):
            continue
        path = path.resolve()
        if path.is_file() and str(path) not in sources:
            sources.append(str(path))
    stem = Path(executable).stem.casefold()
    stems = {stem}
    if stem.endswith('-debug'):
        stems.add(stem[:-6])
    matches = [p for p in sources if Path(p).stem.casefold() in stems]
    generated = [p for p in matches if Path(p).suffix.lower() == '.cbsql']
    if len(generated) == 1:
        return generated[0], sources
    if len(matches) == 1:
        return matches[0], sources
    if len(sources) == 1:
        return sources[0], sources
    return None, sources
