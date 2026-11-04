"""Small recursive parser for GDB/MI2 records; no third-party dependencies."""
import ast
import re

class Parser:
    def __init__(self, text):
        self.text, self.i = text, 0

    def string(self):
        start = self.i
        self.i += 1
        while self.i < len(self.text):
            ch = self.text[self.i]
            self.i += 1
            if ch == '\\':
                self.i += 1
            elif ch == '"':
                return ast.literal_eval(self.text[start:self.i])
        raise ValueError("Unterminated MI string")

    def result(self):
        match = re.match(r'[\w-]+=', self.text[self.i:])
        if not match:
            raise ValueError("Expected MI result")
        key = match[0][:-1]
        self.i += len(match[0])
        return key, self.value()

    def value(self):
        ch = self.text[self.i]
        if ch == '"':
            return self.string()
        if ch not in '{[':
            raise ValueError("Expected MI value")
        self.i += 1
        end = '}' if ch == '{' else ']'
        values = {} if ch == '{' else []
        while self.i < len(self.text) and self.text[self.i] != end:
            if re.match(r'[\w-]+=', self.text[self.i:]):
                key, value = self.result()
                if isinstance(values, dict):
                    values[key] = value
                else:
                    values.append({key: value})
            else:
                if isinstance(values, dict):
                    raise ValueError("Expected tuple result")
                values.append(self.value())
            if self.i < len(self.text) and self.text[self.i] == ',':
                self.i += 1
            elif self.i < len(self.text) and self.text[self.i] != end:
                raise ValueError("Expected separator")
        if self.i >= len(self.text):
            raise ValueError("Unterminated MI container")
        self.i += 1
        return values

    def results(self):
        result = {}
        while self.i < len(self.text):
            key, value = self.result()
            result[key] = value
            if self.i == len(self.text):
                break
            if self.text[self.i] != ',':
                raise ValueError("Expected comma")
            self.i += 1
        return result

def parse_record(line):
    line = line.rstrip('\r\n')
    if not line or line.strip() == '(gdb)':
        return None
    match = re.match(r'(\d*)([\^*+=~@&])(.*)', line)
    if not match:
        return {'kind': 'output', 'text': line}
    token, kind, body = match.groups()
    record = {'kind': kind, 'token': int(token) if token else None}
    if kind in '~@&':
        record['text'] = Parser(body).string()
    else:
        cls, sep, tail = body.partition(',')
        record.update(cls=cls, data=Parser(tail).results() if sep else {})
    return record
