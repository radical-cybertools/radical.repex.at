import re
import os
import sys
import subprocess
from distutils.core import setup
from setuptools import setup, find_packages

def get_version():

    v_long = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
    v_short = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'])

    VERSIONFILE="src/radical/repex/_version.py"
    verstrline = open(VERSIONFILE, "rt").read()
    VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
    mo = re.search(VSRE, verstrline, re.M)

    brach_str = subprocess.check_output(['git', 'branch'])
    brach_str =  brach_str.split(' ')

    branch = ''
    current = 0
    for i in range(len(brach_str)):
        if current == 1:
            branch += branch + brach_str[i] 
            current = 0
        if brach_str[i].startswith('*'):
            current = 1
    branch = branch[:-1]

    if mo:
        verstr = mo.group(1)
        verstr = verstr + '@' + branch + '@' + v_short
    else:
        raise RuntimeError("Unable to find version string in %s." % (VERSIONFILE,))
    return verstr

setup(
    name='radical.repex',
    version='0.3.0',
    author='Antons Treikalis',
    author_email='antons.treikalis@gmail.com',
    packages=['repex_utils', 
              'repex', 
              'replicas', 
              'application_management_modules', 
              'ram_namd',
              'ram_amber'],
    package_dir={'repex_utils': 'src/radical/repex/repex_utils',
                 'repex': 'src/radical/repex',
                 'replicas': 'src/radical/repex/replicas',
                 'application_management_modules': 'src/radical/repex/application_management_modules',
                 'ram_namd': 'src/radical/repex/remote_application_modules/ram_namd',
                 'ram_amber': 'src/radical/repex/remote_application_modules/ram_amber'},
    scripts=['bin/repex-version', 
             'bin/repex-amber', 
             'bin/repex-namd',
             'bin/calc-acceptance-ratio',
             'bin/calc-state-mixing',
             'bin/calc-exchange-metrics'],
    license='LICENSE.md',
    description='Radical Pilot based Replica Exchange Simulations Package',
    long_description=open('README.md').read(),
    install_requires=['radical.pilot', 'mpi4py'],
    url = 'https://github.com/radical-cybertools/radical.repex.git'
)
