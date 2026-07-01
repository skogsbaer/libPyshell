#!/usr/bin/env python

from setuptools import setup

VERSION = '0.6.0'

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(name='libPyshell',
      version=VERSION,
      description='Support for writing shell scripts in Python',
      long_description=long_description,
      long_description_content_type="text/markdown",
      author='Stefan Wehr',
      author_email='stefan.wehr@gmail.com',
      url='https://github.com/skogsbaer/libPyshell',
      package_dir={'shell': 'src'},
      packages=['shell'],
      # PEP 561: ship the py.typed marker so type checkers treat the
      # package as typed for downstream consumers.
      package_data={'shell': ['py.typed']},
      zip_safe=False,
      python_requires='>=3.9'
      )
