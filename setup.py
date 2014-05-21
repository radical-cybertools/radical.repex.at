from distutils.core import setup
from setuptools import setup, find_packages

setup(
    name='re_module',
    version='0.1',
    author='Antons Treikalis',
    author_email='at646@scarletmail.rutgers.edu',
    packages=['re_module'],
    scripts=[],
    license='LICENSE.txt',
    description='Radical Pilot based Replica Exchange module',
    long_description=open('README.md').read(),
    install_requires=['radical.pilot'],
)
