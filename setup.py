#!/usr/bin/env python

from setuptools import setup

setup(name='python-pushover',
      version='0.1',
      description='Comprehensive implementation of the Pushover API',
      long_description=open("README.rst").read() + "\n" + open("CHANGES").read(),
      url='https://github.com/Thibauth/python-pushover',
      author='Thibaut Horel',
      author_email='thibaut+pushover@gmail.com',
      py_modules=['pushover'],
      entry_points={"console_scripts": ["pushover = pushover:main"]},
      install_requires=['requests'],
      license='GNU GPLv3'
      )
