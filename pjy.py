#!/usr/bin/env python3

import ast
import sys
import json
import json.decoder
import json.scanner
from collections import OrderedDict


class Placeholder(object):
    def __init__(self, func=None):
        self._func = func or (lambda x: x)

    def __add__(self, v):
        return Placeholder(lambda x: self(x) + v)

    def __sub__(self, v):
        return Placeholder(lambda x: self(x) - v)

    def __mul__(self, v):
        return Placeholder(lambda x: self(x) * v)

    def __truediv__(self, v):
        return Placeholder(lambda x: self(x) / v)

    def __eq__(self, v):
        return Placeholder(lambda x: self(x) == v)

    def __ne__(self, v):
        return Placeholder(lambda x: self(x) != v)

    def __le__(self, v):
        return Placeholder(lambda x: self(x) <= v)

    def __lt__(self, v):
        return Placeholder(lambda x: self(x) < v)

    def __ge__(self, v):
        return Placeholder(lambda x: self(x) >= v)

    def __gt__(self, v):
        return Placeholder(lambda x: self(x) > v)

    def __getattr__(self, v):
        return Placeholder(lambda x: getattr(self(x), v))

    def __getitem__(self, v):
        return Placeholder(lambda x: self(x)[v])

    def __call__(self, v):
        return self._func(v)


class Dict(OrderedDict):
    @property
    class c(object):
        def __init__(self, d):
            object.__setattr__(self, '_dict', d)

        def __iter__(self):
            return iter(self._dict.keys())

        def __getattr__(self, prop):
            return self._dict[prop]

        def __setattr__(self, prop, val):
            self._dict[prop] = val

    def __getattr__(self, prop):
        return self[prop]

    def __setattr__(self, prop, val):
        self[prop] = val

    def __or__(self, expr):
        return Dict((k, expr(v)) for k, v in self.items())


class Array(list):
    def __or__(self, expr):
        return Array(expr(i) for i in self)


def parse_array(*args, **kwargs):
    arr, v = json.decoder.JSONArray(*args, **kwargs)
    return Array(arr), v


class Decoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super(Decoder, self).__init__(*args, **kwargs)
        self.parse_array = parse_array
        self.scan_once = json.scanner.py_make_scanner(self)


def encode(obj):
    if hasattr(obj, '__iter__'):
        return list(obj)


class Injector(ast.NodeTransformer):
    def call_ListComp(self, node):
        genex = ast.GeneratorExp(elt=node.elt, generators=node.generators)
        n = ast.Name(id='list', ctx=ast.Load())
        return ast.Call(func=n, args=[genex])

    def call_DictComp(self, node):
        n = ast.Name(id='dist', ctx=ast.Load())
        return ast.Call(func=n, args=[node])


def parse_and_inject(src):
    node = ast.parse(src, '<eval>', 'eval')
    return Injector().visit(node)


def main():
    node = parse_and_inject(sys.argv[1])
    code = compile(node, '<eval>', mode='eval')

    with open(sys.argv[2]) as fd:
        data = json.load(fd, cls=Decoder, object_pairs_hook=Dict)

    vars = {
        'd': data,
        '_': Placeholder(),
        'list': Array,
        'dict': Dict,
    }

    res = eval(code, vars)
    print(json.dumps(res, indent=2, default=encode))


if __name__ == '__main__':
    main()
