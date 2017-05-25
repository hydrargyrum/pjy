#!/usr/bin/env python3
# This file is licensed under the WTFPLv2 [http://wtfpl.net]

import ast
import sys
import json
import json.decoder
import json.scanner
from collections import OrderedDict


class Placeholder(object):
    def __init__(self, func=None):
        self._func = func or (lambda x: x)

    # math binary ops
    def __add__(self, v):
        return Placeholder(lambda x: self(x) + v)

    def __radd__(self, v):
        return Placeholder(lambda x: v + self(x))

    def __sub__(self, v):
        return Placeholder(lambda x: self(x) - v)

    def __rsub__(self, v):
        return Placeholder(lambda x: v - self(x))

    def __mul__(self, v):
        return Placeholder(lambda x: self(x) * v)

    def __rmul__(self, v):
        return Placeholder(lambda x: v * self(x))

    def __truediv__(self, v):
        return Placeholder(lambda x: self(x) / v)

    def __rtruediv__(self, v):
        return Placeholder(lambda x: v / self(x))

    def __floordiv__(self, v):
        return Placeholder(lambda x: self(x) // v)

    def __rfloordiv__(self, v):
        return Placeholder(lambda x: v // self(x))

    def __mod__(self, v):
        return Placeholder(lambda x: self(x) % v)

    def __rmod__(self, v):
        return Placeholder(lambda x: v % self(x))

    # math unary ops
    def __neg__(self):
        return Placeholder(lambda x: -self(x))

    def __pos__(self):
        return Placeholder(lambda x: +self(x))

    # math funcs
    def __abs__(self):
        return Placeholder(lambda x: abs(self(x)))

    # comparison ops
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

    # object ops
    def __getattr__(self, v):
        return Placeholder(lambda x: getattr(self(x), v))

    # container ops
    def __getitem__(self, v):
        return Placeholder(lambda x: self(x)[v])

    # evaluation!
    def __call__(self, v):
        return self._func(v)


def partial_placeholder(callee, *args):
    def ret(x):
        new_args = (arg(x) if isinstance(arg, Placeholder) else arg for arg in args)
        return callee(*new_args)

    return Placeholder(ret)


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
        'p': partial_placeholder,
        'partial': partial_placeholder,
    }

    res = eval(code, vars)
    print(json.dumps(res, indent=2, default=encode))


if __name__ == '__main__':
    main()
