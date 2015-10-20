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

#-------------------------------------------------------------------------------
#
# borrowed from the MoinMoin-wiki installer
#
def makeDataFiles(prefix, dir):
    """ Create distutils data_files structure from dir
    distutil will copy all file rooted under dir into prefix, excluding
    dir itself, just like 'ditto src dst' works, and unlike 'cp -r src
    dst, which copy src into dst'.
    Typical usage:
        # install the contents of 'wiki' under sys.prefix+'share/moin'
        data_files = makeDataFiles('share/moin', 'wiki')
    For this directory structure:
        root
            file1
            file2
            dir
                file
                subdir
                    file
    makeDataFiles('prefix', 'root')  will create this distutil data_files structure:
        [('prefix', ['file1', 'file2']),
         ('prefix/dir', ['file']),
         ('prefix/dir/subdir', ['file'])]
    """
    # Strip 'dir/' from of path before joining with prefix
    dir = dir.rstrip('/')
    strip = len(dir) + 1
    found = []
    os.path.walk(dir, visit, (prefix, strip, found))
    return found

def visit((prefix, strip, found), dirname, names):
    """ Visit directory, create distutil tuple
    Add distutil tuple for each directory using this format:
        (destination, [dirname/file1, dirname/file2, ...])
    distutil will copy later file1, file2, ... info destination.
    """
    files = []
    # Iterate over a copy of names, modify names
    for name in names[:]:
        path = os.path.join(dirname, name)
        # Ignore directories -  we will visit later
        if os.path.isdir(path):
            # Remove directories we don't want to visit later
            if isbad(name):
                names.remove(name)
            continue
        elif isgood(name):
            files.append(path)
    destination = os.path.join(prefix, dirname[strip:])
    found.append((destination, files))

def isbad(name):
    """ Whether name should not be installed """
    return (name.startswith('.') or
            name.startswith('#') or
            name.endswith('.pickle') or
            name == 'CVS')

def isgood(name):
    """ Whether name should be installed """
    if not isbad(name):
        if name.endswith('.py') or name.endswith('.json'):
            return True
    return False

#-------------------------------------------------------------------------------

setup(
    name='radical.repex',
    version='0.2.6',
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
                 'amber_kernels_us': 'src/radical/repex/md_kernels/amber_kernels_us',
                 'amber_kernels_3d_tuu': 'src/radical/repex/md_kernels/amber_kernels_3d_tuu',
                 'amber_kernels_3d_tsu': 'src/radical/repex/md_kernels/amber_kernels_3d_tsu'},
    scripts=['bin/repex-version', 'bin/repex-amber'],
    license='LICENSE.txt',
    description='Radical Pilot based Replica Exchange Simulations Package',
    install_requires=['radical.pilot'],
    download_url = 'https://github.com/AntonsT/radical.repex/tarball/0.2',
    url = 'https://github.com/radical-cybertools/radical.repex.git',
    data_files=makeDataFiles('share/radical.repex/examples/', 'examples')
)
