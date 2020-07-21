#!/usr/bin/env python

from setuptools import setup

long_description = "\n".join([open(f).read() for f in ("README.rst", "AUTHORS.rst", "CHANGES.rst")])
setup(
    name="python-pushover",
    version="1.0",
    description="Comprehensive bindings and command line utility for the "
    "Pushover notification service",
    long_description=long_description,
    url="https://github.com/Thibauth/python-pushover",
    author="Thibaut Horel",
    author_email="thibaut.horel+pushover@gmail.com",
    packages=["pushover"],
    entry_points={"console_scripts": ["pushover = pushover.cli:main"]},
    install_requires=["requests>=1.0"],
    license="GNU GPLv3",
)
