#!/usr/bin/env python3
# this project is licensed under the WTFPLv2, see COPYING.txt for details

import glob
import os

from setuptools import setup, find_packages


with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as fd:
    README = fd.read().strip()


setup(
    name='pjy',
    version='0.10.0', # $version

    description='pjy - command-line JSON processor',
    long_description=README,
    url='https://github.com/hydrargyrum/pjy',
    author='Hg',
    license='WTFPLv2',
    classifiers=[
        'Development Status :: 4 - Beta',

        'Environment :: Console',

        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',

        'License :: Public Domain',

        'Topic :: Utilities',
        'Topic :: Text Processing :: Filters',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    keywords='json processor query filter jq',

    python_requires=">=3",
    packages=find_packages(),
    scripts=['pjy'],
    data_files=[
        ('share/doc/pjy', ['README.rst']),
    ],

    extras_requires={
        'pygments': ['pygments'],
    },
)
