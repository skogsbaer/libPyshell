#!/usr/bin/env python

from distutils.core import setup

VERSION = '0.1.3'

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(name='libPyshell',
      version=VERSION,
      description='Support for writing shell scripts in Python',
      long_description=long_description,
      long_description_content_type="text/markdown",
      author='Stefan Wehr',
      author_email='stefan.wehr@unknown.invalid',
      url='https://github.com/skogsbaer/libPyshell',
      package_dir={'shell': 'src'},
      packages=['shell'],
      python_requires='>=3.6'
      )
