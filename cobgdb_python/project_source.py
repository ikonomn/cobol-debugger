"""Small COBOL source inspection for compiler mode and SQL preprocessing."""
from pathlib import Path
import re

LEXEME = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|\*>.*|[\w/-]+|\.")
FORMAT = re.compile(r'>>\s*SOURCE\s+(?:FORMAT\s+)?(?:IS\s+)?(FREE|FIXED)', re.I)


def tokens(source, free=False):
    result = []
    for line in Path(source).read_text(encoding='utf-8', errors='replace').splitlines():
        directive = FORMAT.search(line)
        if directive:
            free = directive[1].upper() == 'FREE'
            continue
        if not free:
            if len(line) > 6 and line[6] in '*/':
                continue
            line = line[7:72]
        for match in LEXEME.finditer(line):
            word = match[0]
            if word.startswith('*>'):
                break
            result.append((word, free))
    return result


def inspect_source(source, directories, free=False, visited=None):
    """Inspect COPY recursively; refuse missing members instead of guessing SQL."""
    source = Path(source).resolve()
    visited = set() if visited is None else visited
    if (source, free) in visited:
        return False, False
    visited.add((source, free))
    items = tokens(source, free)
    words = [word.upper() for word, _ in items]
    sql = any(words[i:i+2] == ['EXEC', 'SQL'] for i in range(len(words)-1))
    module = any(words[i:i+3] == ['PROCEDURE', 'DIVISION', 'USING'] for i in range(len(words)-2))
    for index, (word, mode) in enumerate(items[:-1]):
        if word.upper() != 'COPY':
            continue
        name = items[index+1][0].strip("'\"")
        member = next((p for directory in [source.parent, *map(Path, directories)]
                       for suffix in ('', '.cpy', '.CPY', '.cob', '.cbl')
                       if (p := directory/(name+suffix)).is_file()), None)
        if member is None:
            raise ValueError(f'Cannot inspect COPY {name} in {source}; configure its copybook path.')
        member_sql, member_module = inspect_source(member, directories, mode, visited)
        sql, module = sql or member_sql, module or member_module
    return sql, module
