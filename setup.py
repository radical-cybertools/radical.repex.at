from distutils.core import setup
from setuptools import setup, find_packages


setup(
    name='RepEx',
    version='0.2',
    author='Antons Treikalis',
    author_email='at646@scarletmail.rutgers.edu',
    packages=['repex_utils', 
              'repex', 
              'replicas',   
              'md_patterns', 
              'remote_modules',
              'amber_tex'],
    package_dir={'repex_utils': 'src/radical/repex/repex_utils',
                 'repex': 'src/radical/repex',
                 'replicas': 'src/radical/repex/replicas',
                 'md_patterns': 'src/radical/repex/md_patterns',
                 'remote_modules': 'src/radical/repex/md_patterns/remote_modules',
                 'amber_tex': 'src/radical/repex/md_patterns/amber_tex'},
    scripts=[],
    license='LICENSE.txt',
    description='Radical Pilot based Replica Exchange Simulations Module',
    long_description=open('README.md').read(),
    install_requires=['radical.pilot']
)
