pjy examples
============

Just pretty-print
-----------------

``d`` is the most basic filter, it represents the whole input::

    pjy 'd' - << EOF
    {"foo":"bar","baz":[1,2,3]}
    EOF

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

    pjy 'd["baz"]' - << EOF
    {"foo":"bar","baz":[1,2,3]}
    EOF

Alternatively, in ``pjy``, dicts keys are also attributes::

    pjy 'd.baz' - << EOF
    {"foo":"bar","baz":[1,2,3]}
    EOF

Both filters will print::

    [
      1,
      2,
      3
    ]

In case a key has a reserved name, like ``import`` (keyword) or ``keys`` (dict method), simply use the bracket form.

Lambda-placeholder
------------------

A special identifier, ``_`` can be used to create lambdas. This identifier will absorb most operations done to it and return a lambda applying them::

    pjy 'map(_ + 3, d.baz)' - << EOF
    {"foo":"bar","baz":[1,2,3]}
    EOF

Is equivalent to::

    pjy 'map((lambda x: x + 3), d.baz)' - << EOF
    {"foo":"bar","baz":[1,2,3]}
    EOF

Which will print::

    [
      2,
      3,
      4
    ]

Pipe-like iteration
-------------------

The pipe (``|``) can be used to iterate on a list, it accepts a function as right operand::

    pjy 'd.baz | _ + 1' - << EOF
    {"foo":"bar","baz":[1,2,3]}
    EOF

Which prints::

    [
      2,
      3,
      4
    ]

It also operates on a dict's values, and returns a dict::

    pjy 'd | (lambda x: repr(x))' - << EOF
    {"foo":"bar","baz":[1,2,3]}
    EOF

The values are replaced by the right operand value, the keys are unchanged::

    {
      "foo": "'bar'",
      "baz": "[1, 2, 3]"
    }

Partial placeholder
-------------------

It's not possible to call a function on a placeholder, for example, ``len(_)`` will not work.
However, it's possible to use the ``partial`` helper to prepare the function call::

    pjy 'd | partial(len, _)' - << EOF
    {"foo":"bar","baz":[1,2,3]}
    EOF

Prints::

    {
      "foo": 3,
      "baz": 3
    }

``partial`` ressembles the ``functools.partial`` function: it returns a function wrapping the function passed as first argument.
The returned function will call the original function with the fixed arguments passed.
The difference is that lambda-placeholders can be passed, and they will be replaced by the wrapper's argument.
