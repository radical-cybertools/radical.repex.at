from distutils.core import setup
from setuptools import setup, find_packages


setup(
    name='RepEx',
    version='0.1',
    author='Antons Treikalis',
    author_email='at646@scarletmail.rutgers.edu',
    packages=['repex_utils', 'repex', 'replicas', 'kernels', 'pilot_kernels', 'md_kernels', 'namd_kernels_tex', 'amber_kernels_tex', 'amber_kernels_salt'],
    package_dir={'repex_utils': 'src/radical/repex/repex_utils',
                 'repex': 'src/radical/repex',
                 'replicas': 'src/radical/repex/replicas',
                 'kernels': 'src/radical/repex/kernels',
                 'pilot_kernels': 'src/radical/repex/pilot_kernels',
                 'md_kernels': 'src/radical/repex/md_kernels',
                 'namd_kernels_tex': 'src/radical/repex/md_kernels/namd_kernels_tex',
                 'amber_kernels_tex': 'src/radical/repex/md_kernels/amber_kernels_tex',
                 'amber_kernels_salt': 'src/radical/repex/md_kernels/amber_kernels_salt'},
    scripts=[],
    license='LICENSE.txt',
    description='Radical Pilot based Replica Exchange Simulations Module',
    long_description=open('README.md').read(),
    #install_requires=['radical.pilot']
)
