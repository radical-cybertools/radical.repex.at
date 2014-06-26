"""
.. module:: radical.repex.namd_kernels.launch_simulation
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import optparse


def parse_command_line():
    """Performs command line parsing.

    Returns:
    options - dictionary {'input_file': 'path/to/input.json'}
    """

    usage = "usage: %prog [Options]"
    parser = optparse.OptionParser(usage=usage)

    parser.add_option('--input',
              dest='input_file',
              help='specifies RadicalPilot, NAMD and RE simulation parameters')

    (options, args) = parser.parse_args()

    if options.input_file is None:
        parser.error("You must specify simulation input file (--input). Try --help for help.")

    return options