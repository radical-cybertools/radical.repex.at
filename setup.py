import re
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
    if mo:
        verstr = mo.group(1)
        verstr = verstr + "@" + v_short
    else:
        raise RuntimeError("Unable to find version string in %s." % (VERSIONFILE,))
    return verstr

#-------------------------------------------------------------------------------

setup(
    name='RepEx',
    version=get_version(),
    author='Antons Treikalis',
    author_email='antons.treikalis@rutgers.edu',
    packages=['repex_utils', 
              'repex', 
              'replicas', 
              'kernels', 
              'pilot_kernels', 
              'md_kernels', 
              'namd_kernels_tex', 
              'amber_kernels_tex', 
              'amber_kernels_salt',
              'amber_kernels_2d',
              'amber_kernels_us',
              'amber_kernels_3d_tuu',
              'amber_kernels_3d_tsu'],
    package_dir={'repex_utils': 'src/radical/repex/repex_utils',
                 'repex': 'src/radical/repex',
                 'replicas': 'src/radical/repex/replicas',
                 'kernels': 'src/radical/repex/kernels',
                 'pilot_kernels': 'src/radical/repex/pilot_kernels',
                 'md_kernels': 'src/radical/repex/md_kernels',
                 'namd_kernels_tex': 'src/radical/repex/md_kernels/namd_kernels_tex',
                 'amber_kernels_tex': 'src/radical/repex/md_kernels/amber_kernels_tex',
                 'amber_kernels_salt': 'src/radical/repex/md_kernels/amber_kernels_salt',
                 'amber_kernels_2d': 'src/radical/repex/md_kernels/amber_kernels_2d',
                 'amber_kernels_us': 'src/radical/repex/md_kernels/amber_kernels_us',
                 'amber_kernels_3d_tuu': 'src/radical/repex/md_kernels/amber_kernels_3d_tuu',
                 'amber_kernels_3d_tsu': 'src/radical/repex/md_kernels/amber_kernels_3d_tsu'},
    scripts=['bin/repex-version'],
    license='LICENSE.txt',
    description='Radical Pilot based Replica Exchange Simulations Module',
    long_description=open('README.md').read(),
    install_requires=['radical.pilot']
)
