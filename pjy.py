#!/usr/bin/env python3
# SPDX-License-Identifier: WTFPL

from argparse import ArgumentParser, FileType
import ast
from collections import OrderedDict
from importlib import import_module
import json
import json.decoder
import json.scanner
import math
import os
import re
import signal
import sys
import traceback

try:
    import pygments
    import pygments.formatters
    import pygments.lexers.data

    def colorize(s):
        lexer = pygments.lexers.data.JsonLexer()
        formatter = pygments.formatters.TerminalFormatter()
        return pygments.highlight(s, lexer, formatter).rstrip()
except ImportError:
    def colorize(s):
        return s


__version__ = '0.13.0'  # $version


def ph_call(obj, x):
    if isinstance(obj, Placeholder):
        return obj(x)
    return obj


class Placeholder(object):
    """Functor that accumulates operations and applies them at the end

    Example:

        (_ + 1) * 2

    is a callable that will return 4 when applied to 1
    """

    def __init__(self, func=None):
        self._func = func or (lambda x: x)

    # math binary ops
    def __add__(self, v):
        return Placeholder(lambda x: self(x) + ph_call(v, x))

    def __radd__(self, v):
        return Placeholder(lambda x: ph_call(v, x) + self(x))

    def __sub__(self, v):
        return Placeholder(lambda x: self(x) - ph_call(v, x))

    def __rsub__(self, v):
        return Placeholder(lambda x: ph_call(v, x) - self(x))

    def __mul__(self, v):
        return Placeholder(lambda x: self(x) * ph_call(v, x))

    def __rmul__(self, v):
        return Placeholder(lambda x: ph_call(v, x) * self(x))

    def __truediv__(self, v):
        return Placeholder(lambda x: self(x) / ph_call(v, x))

    def __rtruediv__(self, v):
        return Placeholder(lambda x: ph_call(v, x) / self(x))

    def __floordiv__(self, v):
        return Placeholder(lambda x: self(x) // ph_call(v, x))

    def __rfloordiv__(self, v):
        return Placeholder(lambda x: ph_call(v, x) // self(x))

    def __mod__(self, v):
        return Placeholder(lambda x: self(x) % ph_call(v, x))

    def __rmod__(self, v):
        return Placeholder(lambda x: ph_call(v, x) % self(x))

    # math unary ops
    def __neg__(self):
        return Placeholder(lambda x: -self(x))

    def __pos__(self):
        return Placeholder(lambda x: +self(x))

    # math funcs
    def __abs__(self):
        return Placeholder(lambda x: abs(self(x)))

    # bit opts
    def __and__(self, v):
        return Placeholder(lambda x: self(x) & ph_call(v, x))

    def __or__(self, v):
        return Placeholder(lambda x: self(x) | ph_call(v, x))

    def __xor__(self, v):
        return Placeholder(lambda x: self(x) ^ ph_call(v, x))

    # comparison ops
    def __eq__(self, v):
        return Placeholder(lambda x: self(x) == ph_call(v, x))

    def __ne__(self, v):
        return Placeholder(lambda x: self(x) != ph_call(v, x))

    def __le__(self, v):
        return Placeholder(lambda x: self(x) <= ph_call(v, x))

    def __lt__(self, v):
        return Placeholder(lambda x: self(x) < ph_call(v, x))

    def __ge__(self, v):
        return Placeholder(lambda x: self(x) >= ph_call(v, x))

    def __gt__(self, v):
        return Placeholder(lambda x: self(x) > ph_call(v, x))

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
    """Ordered dict whose items are attributes too"""
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

    def __getitem__(self, prop):
        return super().get(prop)

    def __getattr__(self, prop):
        return super().get(prop)

    def __setattr__(self, prop, val):
        self[prop] = val

    def __or__(self, expr):
        return Dict((k, expr(v)) for k, v in self.items())

    def __and__(self, expr):
        return Dict((k, v) for k, v in self.items() if expr(v))

    def update(self, *args, **kwargs):
        """Like regular dict.update() but returns the dict

        Useful for chaining calls.
        """
        super(Dict, self).update(*args, **kwargs)
        return self


class Array(list):
    def __or__(self, expr):
        return Array(expr(i) for i in self)

    def __and__(self, expr):
        return Array(i for i in self if expr(i))

    def __getitem__(self, index):
        try:
            return super().__getitem__(index)
        except IndexError:
            return None


def parse_array(*args, **kwargs):
    arr, v = json.decoder.JSONArray(*args, **kwargs)
    return Array(arr), v


class Decoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super(Decoder, self).__init__(*args, **kwargs)
        # can't use a method, the super ctor would overwrite it...
        self.parse_array = parse_array
        # at least, the "py" scanner uses our configuration
        self.scan_once = json.scanner.py_make_scanner(self)


def convert_to_jsonable(obj):
    if hasattr(obj, '__iter__'):
        return list(obj)
    return repr(obj)


class Injector(ast.NodeTransformer):
    # convert list and dict literals to our Array and Dict

    def visit_List(self, node):
        self.generic_visit(node)

        n = ast.Name(id='list', ctx=ast.Load())
        return ast.Call(func=n, args=[node], keywords=[])

    def visit_Dict(self, node):
        self.generic_visit(node)

        n = ast.Name(id='dict', ctx=ast.Load())
        return ast.Call(func=n, args=[node], keywords=[])

    def visit_ListComp(self, node):
        self.generic_visit(node)

        genex = ast.GeneratorExp(elt=node.elt, generators=node.generators)
        n = ast.Name(id='list', ctx=ast.Load())
        return ast.Call(func=n, args=[genex], keywords=[])

    def visit_DictComp(self, node):
        self.generic_visit(node)

        n = ast.Name(id='dict', ctx=ast.Load())
        return ast.Call(func=n, args=[node], keywords=[])


def parse_and_inject(src):
    node = ast.parse(src, '<eval>', 'eval')
    return Injector().visit(node)


def load_rc():
    dirs = [os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')]
    dirs.extend((os.environ.get('XDG_CONFIG_HOME') or '/etc/xdg').split(':'))

    for dir in filter(None, dirs):
        path = os.path.join(dir, 'pjy', 'lib.py')
        if os.path.isfile(path):
            with open(path) as fd:
                node = ast.parse(fd.read(), path, 'exec')
                Injector().visit(node)
                ast.fix_missing_locations(node)
                code = compile(node, path, 'exec')
                d = {
                    'list': Array,
                    'dict': Dict,
                    '_': Placeholder(),
                }
                exec(code, d)
                return d
    return {}


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # arguments
    argparser = ArgumentParser()
    argparser.add_argument('expr', nargs='?', default='d')
    argparser.add_argument('files', nargs='*', default='-', type=FileType('r'))
    argparser.add_argument('--version', action='version', version=__version__)
    argparser.add_argument('--ascii', '--ascii-output', action='store_true')
    argparser.add_argument('--monochrome-output', action='store_true')
    grp = argparser.add_mutually_exclusive_group()
    grp.add_argument('--tab', help='Use tabs for indentation', action='store_true')
    grp.add_argument('--indent', type=int, help='Use the number of spaces for indentation')
    grp.add_argument(
        '--compact-output', dest='compact', action='store_true',
        help='No indentation or whitespace between elements, JSON on a single line',
    )
    argparser.add_argument(
        '--null-input', action='store_true',
        help="Don't read any input, act as if the input was just null/None",
    )
    argparser.add_argument(
        '--raw-output', action='store_true',
        help='If result is a string, print directly, not as JSON',
    )
    argparser.add_argument(
        '--arg', nargs=2,
        action='append', dest='user_vars',
        metavar='VAR',
        help='Inject a variable with a value in the expression',
    )
    args = argparser.parse_args()

    do_parse_indent(args)
    code = do_parse_expression(args)
    inputs = do_inputs(args)
    vars = do_prepare_runtime(inputs, args)
    res = do_eval(code, vars, args)
    do_output(res, args)


def do_parse_indent(args):
    args.separators = None
    if args.compact:
        args.indent = None
        args.separators = (',', ':')
    elif args.tab:
        args.indent = '\t'
    elif args.indent is None:
        args.indent = 2


def do_parse_expression(args):
    try:
        node = parse_and_inject(args.expr)
    except SyntaxError:
        traceback.print_exc(limit=0)
        sys.exit(os.EX_USAGE)

    ast.fix_missing_locations(node)
    code = compile(node, '<eval>', mode='eval')
    return code


def do_inputs(args):
    if args.null_input:
        return [None]

    inputs = []

    for fd in args.files:
        if fd == '-':
            fd = FileType('r')('-')
        fn = fd.name
        try:
            with fd:
                data = json.load(fd, cls=Decoder, object_pairs_hook=Dict)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            print('Cannot decode JSON data in %s: %s' % (fn, e), file=sys.stderr)
            sys.exit(os.EX_DATAERR)
        except IOError as e:
            print('Cannot read %s: %s' % (fn, e), file=sys.stderr)
            sys.exit(os.EX_IOERR)

        inputs.append(data)

    return inputs


def do_prepare_runtime(inputs, args):
    try:
        vars = load_rc()
    except Exception as e:
        print('Cannot execute config file: %s' % e, file=sys.stderr)
        vars = {}

    vars.update({
        'data': inputs[0],
        'd': inputs[0],
        'inputs': inputs,

        'list': Array,
        'dict': Dict,

        '_': Placeholder(),
        'p': partial_placeholder,
        'partial': partial_placeholder,

        'imp': import_module,
        'math': math,
        're': re,
    })
    for user_var, user_val in (args.user_vars or []):
        vars[user_var] = user_val

    return vars


def do_eval(code, vars, args):
    try:
        res = eval(code, vars)
    except Exception as e:
        lines = traceback.format_list(traceback.extract_tb(sys.exc_info()[2])[1:])
        print(''.join(lines), end='', file=sys.stderr)
        print('%s: %s' % (type(e).__name__, e), file=sys.stderr)
        sys.exit(os.EX_DATAERR)

    return res


def do_output(res, args):
    # output
    color = not (args.monochrome_output or os.getenv("NO_COLOR"))
    if args.raw_output and isinstance(res, str):
        color = False
        s = res
    else:
        s = json.dumps(
            res,
            default=convert_to_jsonable,
            indent=args.indent,
            separators=args.separators,
            ensure_ascii=bool(args.ascii),
        )
    try:
        if color and sys.stdout.isatty():
            print(colorize(s))
        else:
            print(s)
        sys.stdout.close()
    except IOError:
        pass


if __name__ == '__main__':
    main()
