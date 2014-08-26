from distutils.core import setup
from setuptools import setup, find_packages


setup(
    name='RepEx',
    version='0.1',
    author='Antons Treikalis',
    author_email='at646@scarletmail.rutgers.edu',
    #packages=find_packages('src'),
    #packages=['src.radical.repex'],
    package_dir={'radical.repex': 'src/radical/repex'},
    scripts=[],
    license='LICENSE.txt',
    description='Radical Pilot based Replica Exchange Simulations Module',
    long_description=open('README.md').read(),
    install_requires=['radical.pilot'],
)
