"""Small source-derived flow model for straight-line COBOL and scoped IF blocks.

This is deliberately not a full COBOL parser. Unsupported control flow is
reported, rather than presented as a complete control-flow graph.
"""
from dataclasses import dataclass, field
import re

@dataclass
class Node:
    id: int
    line: int
    end_line: int
    text: str
    kind: str
    lane: int = 0

@dataclass
class Flow:
    nodes: list = field(default_factory=list)
    edges: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def at_line(self, line):
        return next((n for n in self.nodes if n.line > 0 and n.line <= line <= n.end_line), None)

def build_flow(text):
    model = Flow()
    tokens = []
    in_procedure = False
    verbs = {'ACCEPT','ADD','CALL','CANCEL','CLOSE','COMPUTE','CONTINUE','DELETE',
             'DISPLAY','DIVIDE','ELSE','END-IF','EVALUATE','EXIT','GOBACK','GO',
             'IF','INITIALISE','INITIALIZE','INSPECT','MOVE','MULTIPLY','OPEN',
             'PERFORM','READ','REWRITE','SEARCH','SET','STOP','STRING','SUBTRACT',
             'UNSTRING','WRITE'}
    for line, raw in enumerate(text.splitlines(), 1):
        if len(raw) > 6 and raw[6] in '*/':
            continue
        content = raw[7:72] if len(raw) >= 7 and raw[:6].strip().isdigit() else raw
        # Conventional blank sequence columns in fixed-format sources.
        if raw.startswith('       '):
            content = raw[7:72]
        # Remove inline comments outside quoted literals.
        content = re.split(r"\*>(?=(?:[^\"']|\"[^\"]*\"|'[^']*')*$)", content, maxsplit=1)[0].strip()
        if not content:
            continue
        upper = content.upper()
        if 'PROCEDURE DIVISION' in upper:
            in_procedure = True
            continue
        if not in_procedure or upper.startswith('END PROGRAM'):
            continue
        word = upper.split()[0].rstrip('.')
        if word in verbs:
            if word in ('PERFORM','EVALUATE','GO','SEARCH','EXIT'):
                model.warnings.append(f'Line {line}: {word} control flow is not expanded.')
            tokens.append([line, line, content, word])
        elif word.startswith('END-'):
            continue
        elif tokens and not re.fullmatch(r'[\w-]+\.', content):
            tokens[-1][1] = line
            tokens[-1][2] += ' ' + content
        elif re.fullmatch(r'[\w-]+\.', content):
            model.warnings.append(f'Line {line}: paragraph label; paragraph calls are not expanded.')

    def node(line, end, text, kind, lane):
        n = Node(len(model.nodes), line, end, text, kind, lane)
        model.nodes.append(n)
        return n.id

    def connect(exits, target):
        for origin, label in exits:
            model.edges.append((origin, target, label))

    start = node(0, 0, 'Start', 'terminal', 0)
    def sequence(index, lane):
        entry = None
        exits = []
        while index < len(tokens):
            line, end, text, word = tokens[index]
            if word in ('ELSE', 'END-IF'):
                break
            kind = 'decision' if word == 'IF' else 'io' if word in ('ACCEPT','DISPLAY','READ','WRITE') else 'terminal' if word in ('GOBACK','STOP') else 'action'
            current = node(line, end, text, kind, lane)
            if entry is None:
                entry = current
            connect(exits, current)
            index += 1
            if word == 'IF':
                yes, yes_exits, index = sequence(index, lane)
                if yes is not None:
                    model.edges.append((current, yes, 'Yes'))
                else:
                    yes_exits = [(current, 'Yes')]
                no_exits = [(current, 'No')]
                if index < len(tokens) and tokens[index][3] == 'ELSE':
                    no, no_exits, index = sequence(index + 1, lane + 1)
                    if no is not None:
                        model.edges.append((current, no, 'No'))
                    else:
                        no_exits = [(current, 'No')]
                if index < len(tokens) and tokens[index][3] == 'END-IF':
                    index += 1
                else:
                    model.warnings.append(f'Line {line}: IF without explicit END-IF; chart may be incomplete.')
                exits = yes_exits + no_exits
            elif kind == 'terminal':
                exits = []
            else:
                exits = [(current, '')]
        return entry, exits, index

    first, exits, index = sequence(0, 0)
    if first is not None:
        model.edges.append((start, first, ''))
    end = node(0, 0, 'End', 'terminal', 0)
    connect(exits, end)
    for terminal in model.nodes:
        if terminal.kind == 'terminal' and terminal.line > 0:
            model.edges.append((terminal.id, end, ''))
    if first is None:
        model.edges.append((start, end, ''))
    if index < len(tokens):
        model.warnings.append('Unmatched ELSE/END-IF: only the parsed portion is shown.')
    return model
