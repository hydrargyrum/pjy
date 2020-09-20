#!/usr/bin/env pytest-3

from json import loads, dumps
import os
from subprocess import check_output
from tempfile import NamedTemporaryFile
from unittest import TestCase


pjy_dict = {}


class TestCommand(TestCase):
    def process(self, expr, input, encode=True, decode=True, args=None):
        if not args:
            args = []

        if encode:
            input = dumps(input).encode('utf-8')

        r = check_output(['./pjy'] + args + [expr], input=input)
        r = r.decode('utf-8')
        if decode:
            r = loads(r)
        return r

    def process_eq(self, expr, input, expected):
        self.assertEqual(expected, self.process(expr, input))

    def test_noop(self):
        inputs = [
            None,
            True,
            False,
            0,
            42,
            "hello world",
            [1, 2, 3],
            {"hello": "world"},
        ]
        for input in inputs:
            self.process_eq('d', input, input)

    def test_basic(self):
        self.process_eq('1', 'hello', 1)
        self.process_eq('d+1', 3, 4)
        self.process_eq('d+"bar"', 'foo', 'foobar')

    def test_list_map(self):
        self.process_eq('d|_+1', list(range(0, 3)), list(range(1, 4)))
        self.process_eq('[0, 1, 2]|_+1', None, list(range(1, 4)))
        self.process_eq('list(range(0, 3))|_+1', None, list(range(1, 4)))
        self.process_eq('[i for i in range(0, 3)]|_+1', None, list(range(1, 4)))

    def test_dict_map(self):
        self.process_eq('d|_+1', {'foo': 1}, {'foo': 2})
        self.process_eq('{"foo":1}|_+1', None, {'foo': 2})
        self.process_eq('dict({"foo": 1})|_+1', None, {'foo': 2})
        self.process_eq('{k: v for k, v in [("foo", 1)]}|_+1', None, {'foo': 2})

    def test_multiple_files(self):
        with NamedTemporaryFile(buffering=0) as f1:
            with NamedTemporaryFile(buffering=0) as f2:
                f1.write(b'1')
                f2.write(b'2')
                r = check_output(['./pjy', 'inputs[0]+inputs[1]', f1.name, f2.name])
                r = loads(r.decode('utf-8'))
                self.assertEqual(r, 3)

    def test_option_ascii(self):
        self.assertEqual(
            '"é"\n',
            self.process('d', 'é', decode=False),
        )
        self.assertEqual(
            '"\\u00e9"\n',
            self.process('d', 'é', args=['--ascii-output'], decode=False),
        )

    def test_option_raw(self):
        self.assertEqual(
            'é\n',
            self.process('d', 'é', args=['--raw-output'], decode=False),
        )
        self.assertEqual(
            '[]\n',
            self.process('d', [], args=['--raw-output'], decode=False),
        )

    def test_option_indentation(self):
        self.assertEqual(
            '[\n  1,\n  2\n]\n',
            self.process('d', [1, 2], decode=False),
        )
        self.assertEqual(
            '[\n    1,\n    2\n]\n',
            self.process('d', [1, 2], args=['--indent', '4'], decode=False),
        )
        self.assertEqual(
            '[\n\t1,\n\t2\n]\n',
            self.process('d', [1, 2], args=['--tab'], decode=False),
        )
        self.assertEqual(
            '[1,2]\n',
            self.process('d', [1, 2], args=['--compact-output'], decode=False),
        )

    def test_option_arg(self):
        self.assertEqual(
            "bar",
            self.process('foo', None, args=['--arg', 'foo', 'bar', '--arg', 'baz', 'qux']),
        )


class TestInternals(TestCase):
    def test_placeholder(self):
        _ = pjy_dict['Placeholder']()

        self.assertEqual(2, _(2))
        self.assertEqual(3, (_ + 1)(2))
        self.assertEqual(3, (1 + _)(2))
        self.assertEqual(6, (2 * (_ + 1))(2))
        self.assertEqual(3, (abs((((_ + 1) - 2) * 3) / 4))(5))
        self.assertEqual([1, 2], (_ + [2])([1]))
        self.assertEqual(1, (_[0])([1]))
        assert (_.append)([])

        self.assertEqual(2, (_ + _)(1))

    def test_list(self):
        _ = pjy_dict['Placeholder']()
        Array = pjy_dict['Array']

        self.assertEqual([2, 3, 4], Array([1, 2, 3]) | (_ + 1))

    def test_dict(self):
        _ = pjy_dict['Placeholder']()
        Dict = pjy_dict['Dict']

        self.assertEqual(42, Dict({'hello': 42}).hello)

        self.assertEqual({'hello': 42, 'world': 53},
            Dict({'hello': 41, 'world': 52}) | (_ + 1))


with open(os.path.join(os.path.dirname(__file__), 'pjy')) as fd:
    code = compile(fd.read(), 'pjy', 'exec')
    exec(code, pjy_dict)
