#!/usr/bin/env python3

from setuptools import setup

setup(name='obsfucate-css-selectors',
    version='1.0',
    description='Utility that rewrites CSS, HTML, and JavaScript files in order to save bytes and obfuscate your code.',
    author='YetAnotherMinion, Craig Campbell',
    author_email='yam@thinkalexandria.com',
    url='https://github.com/ThinkAlexandria/obsfucate-css-selectors',
    packages=['ruminatecss'],
    install_requires=["tinycss2", "beautifulsoup4", "slimit"],
    scripts=['obsfucate-css-selectors']
)
