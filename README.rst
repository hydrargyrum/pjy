pjy - JSON Python processor
===========================

``pjy`` is a command-line tool to process JSON data and execute queries on it.
It is a bit like `jq <https://stedolan.github.io/jq/>`_ but with a Python syntax for queries.

Install
+++++++

From `PyPI <https://pypi.org/project/pjy/>`_::

    pip install pjy

Usage
+++++

    pjy [EXPR] [FILES]

``pjy`` will read JSON data from ``FILES`` and print the evaluation result of the Python expression ``EXPR``.

If ``FILES`` is missing or is "``-``", pjy will use stdin.

The simplest expression to use, which outputs the input unchanged is "``d``" (for data).

It's possible to use multiple input files.

Examples
++++++++

In ``pjy``, expressions are also called "filters", as in ``jq``.

Just pretty-print
-----------------

``d`` (short for "data") is the most basic filter, it represents the whole input::

    pjy 'd'
        {"foo":"bar","baz":[1,2,3]}

Prints::

    {
      "foo": "bar",
      "baz": [
        1,
        2,
        3
      ]
    }

Select a dict key
-----------------

The filters are Python expressions, hence we can select a dict key::

    pjy 'd["baz"]'
        {"foo":"bar","baz":[1,2,3]}

Alternatively, in ``pjy``, dicts keys are also attributes::

    pjy 'd.baz'
        {"foo":"bar","baz":[1,2,3]}

Both filters will print::

    [
      1,
      2,
      3
    ]

In case a key has a reserved name, like ``import`` (keyword) or ``keys`` (dict method), simply use the bracket form.

Non-existent keys
-----------------

Non-existent keys::

    pjy 'd.baz'
        {"foo":"bar"}

will return ``None``::

    null

Same for out-of-bounds indices::

    pjy 'd[3]'
        [1, 2]

Do a basic operation
--------------------

It's possible to use everything that a Python expression can contain::

    pjy '[i + 1 for i in d["baz"]]'
        {"foo":"bar","baz":[1,2,3]}

Prints::

    [
      2,
      3,
      4
    ]

Lambda-placeholder
------------------

A special identifier, ``_`` can be used to create lambdas. This identifier will absorb most operations done to it and return a lambda applying them.
Then, the returned lambda can be applied::

    pjy 'map(_ + 1, d.baz)'
        {"foo":"bar","baz":[1,2,3]}

Is equivalent to::

    pjy 'map((lambda x: x + 1), d.baz)'
        {"foo":"bar","baz":[1,2,3]}

Which will print::

    [
      2,
      3,
      4
    ]

The lambda-placeholder will absorb chained operations::

    pjy 'map((_ + 1) * 2, d.baz)'
        {"foo":"bar","baz":[1,2,3]}


Will result in::

    [
      4,
      6,
      8
    ]

And::

    pjy 'map(_[1:3] * 2, d)'
        {"foo":"bar","baz":[1,2,3]}

Will return::

    {
      "foo": "arar",
      "baz": [
        2,
        3,
        2,
        3
      ]
    }

Pipe-like iteration
-------------------

The pipe (``|``) can be used to iterate on a list, it accepts a function as right operand::

    pjy 'd.baz | _ + 1'
        {"foo":"bar","baz":[1,2,3]}

Which prints::

    [
      2,
      3,
      4
    ]

It also operates on a dict's values, and returns a dict::

    pjy 'd | (lambda x: repr(x))'
        {"foo":"bar","baz":[1,2,3]}

The values are replaced by the right operand value, the keys are unchanged::

    {
      "foo": "'bar'",
      "baz": "[1, 2, 3]"
    }

Ampersand for filtering
-----------------------

Similar to the pipe, the ampersand (``&``) is used on a list and a function, but its purpose is to filter::

    pjy 'd & (_ % 2 == 0)'
        [0, 1, 2, 3]

outputs::

    [
      0,
      2
    ]

Which is equivalent to running::

    pjy 'filter(_ % 2 == 0, d)'
        [0, 1, 2, 3]

Like the pipe, it works on a dict, and the filter is applied on the dict values.

Partial placeholder
-------------------

It's not possible to call a function on a placeholder, for example, ``len(_)`` will not work.
However, it's possible to use the ``partial`` helper to prepare the function call::

    pjy 'd | partial(len, _)'
        {"foo":"bar","baz":[1,2,3]}

Prints::

    {
      "foo": 3,
      "baz": 3
    }

``partial`` ressembles the ``functools.partial`` function: it returns a function wrapping the function passed as first argument.
The returned function will call the original function with the fixed arguments passed.
The difference is that lambda-placeholders can be passed, and they will be replaced by the wrapper's argument.

``p`` is a short alias for the ``partial`` function which can be used in pjy expressions.

Imports
-------

It's possible to import modules with the ``imp`` function::

   pjy 'filter(p(imp("fnmatch").fnmatch, _, "f*"), d.keys())'
        {"foo":"bar","baz":[1,2,3]}

Will print::

    [
      "foo"
    ]

The ``math`` and ``re`` modules are already imported and available directly without having to call ``imp``.

Multiple inputs
---------------

In ``pjy``, an ``inputs`` variable exists, which is a list containing the JSON data of each input file passed on the command line.
The ``d`` variable is simply an alias to ``inputs[0]``.

For example::

    pjy 'filter(_[0] != _[1], zip(inputs[0], inputs[1]))' before.json after.json

will read 2 files ``before.json`` and ``after.json``, which consist in a list of objects, and ``pjy`` will compare each zipped-pair of objects together.
Then it will print the list of differing pairs.

Options
+++++++

Input options
-------------

	``--null-input``

Don't read any input, act as if the input was only ``null``.

	``--arg VAR VALUE``

Inject a variable named VAR with a VALUE in the expression.

Output options
--------------

	``--monochrome-output``

Force no colors even if output is a TTY.

	``--ascii-output``

When outputting non-ASCII strings, use ``\uXXXX`` notation instead of directly Unicode characters by default.

	``--tab``

Indent output with tabs instead of 2 spaces.

	``--indent N``

Indent output with N spaces instead of 2 spaces.

	``--compact-output``

Don't indent output and don't add extra whitespace between key/values and list elements.


Security
++++++++

``pjy`` by itself does not write files (except stdout/stderr) or sockets, or run external commands.
However, ``pjy`` runs the given expressions passed as argument, in the Python interpreter, without a sandbox.
Hence, do NOT pass dangerous or untrusted Python expressions to ``pjy``.

Dependencies
++++++++++++

``pjy`` is written in Python 3. Its ``setup.py`` requires ``setuptools``.

If ``pygments`` is installed, ``pjy``'s output will be colorized, but it's entirely optional.

Version and license
+++++++++++++++++++

.. $version

``pjy`` is at version 0.13.0, it uses `semantic versioning <http://semver.org/>`_.
It is licensed under the WTFPLv2, see COPYING.WTFPL for license text.
