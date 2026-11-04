import unittest
from cobgdb_python.mi import parse_record

class MITests(unittest.TestCase):
    def test_nested_records(self):
        record = parse_record('12^done,stack=[frame={level="0",fullname="C:\\\\src\\\\hello.cob",line="7"},frame={level="1"}]')
        self.assertEqual(record['token'], 12)
        self.assertEqual(record['data']['stack'][0]['frame']['line'], '7')
        self.assertEqual(len(record['data']['stack']), 2)

    def test_stream(self):
        self.assertEqual(parse_record('~"hello\\n"')['text'], 'hello\n')

    def test_async(self):
        self.assertEqual(parse_record('*stopped,reason="breakpoint-hit"')['data']['reason'], 'breakpoint-hit')

    def test_bad_container(self):
        with self.assertRaises(ValueError):
            parse_record('1^done,x=["a"')

    def test_prompt(self):
        self.assertIsNone(parse_record('(gdb) '))
