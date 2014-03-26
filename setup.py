from distutils.core import setup

setup(
    name='re_package',
    version='0.1',
    author='Antons Treikalis',
    author_email='at646@scarletmail.rutgers.edu',
    packages=['re_package','examples'],
    scripts=[],
    license='LICENSE.txt',
    description='Radical Pilot based Replica Exchange package',
    long_description=open('README.md').read(),
    install_requires=[
        "Python >= 2.6.5"
    ],
)
