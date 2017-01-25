"""
.. module:: radical.repex.namd_kernels.launch_simulation
.. moduleauthor::  <antons.treikalis@gmail.com>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import optparse


def parse_cmd_repex():
    """Performs command line parsing.

    Returns:
        options - dictionary {'input_file': 'path/to/input.json'}
    """

    usage = "usage: %prog [Options]"
    parser = optparse.OptionParser(usage=usage)

    parser.add_option('--input',
                      dest='remd_input',
                      help='specifies RepEx simulation parameters')

    parser.add_option('--rconfig',
                      dest='resource_config',
                      help='specifies options to access remote resource')

    (options, args) = parser.parse_args()

    if options.remd_input is None:
        parser.error("You must specify simulation input file (--input). Try --help for help.")

    if options.resource_config is None:
        parser.error("You must specify resource configuration file (--rconfig). Try --help for help.")

    return options

def parse_cmd_acc_ratio():
    """Performs command line parsing.

    Returns:
        options - dictionary {'input_file': 'path/to/input.json'}
    """

    usage = "usage: %prog [Options]"
    parser = optparse.OptionParser(usage=usage)

    parser.add_option('--replicas',
                      dest='nr_replicas',
                      help='total number of replicas')

    parser.add_option('--filename',
                      dest='filename',
                      help='name of the pairs_for_exchange file')

    (options, args) = parser.parse_args()

    if options.nr_replicas is None:
        parser.error("You must specify the total number of replicas (--replicas). Try --help for help.")

    if options.filename is None:
        parser.error("You must specify the name of the pairs_for_exchange file (--filename). Try --help for help.")

    return options

def parse_cmd_state_mixing():
    """Performs command line parsing.

    Returns:
        options - dictionary {'input_file': 'path/to/input.json'}
    """

    usage = "usage: %prog [Options]"
    parser = optparse.OptionParser(usage=usage)

    parser.add_option('--replicas',
                      dest='nr_replicas',
                      help='total number of replicas')

    parser.add_option('--states',
                      dest='nr_states',
                      help='number of states in this dimension')

    parser.add_option('--filenames',
                      dest='filenames',
                      help='comma-separated, ordered list of names of the pairs_for_exchange files')

    (options, args) = parser.parse_args()

    if options.nr_replicas is None:
        parser.error("You must specify the total number of replicas (--replicas). Try --help for help.")

    if options.nr_states is None:
        parser.error("You must specify the number of states in this dimension (--states). Try --help for help.")

    if options.filenames is None:
        parser.error("You must specify names of the pairs_for_exchange files (--filename). Try --help for help.")

    return options


def parse_cmd_count_exchange_metrics():
    """Performs command line parsing.

    Returns:
        options - dictionary {'input_file': 'path/to/input.json'}
    """

    usage = "usage: %prog [Options]"
    parser = optparse.OptionParser(usage=usage)

    parser.add_option('--replicas',
                      dest='nr_replicas',
                      help='total number of replicas')

    parser.add_option('--files',
                      dest='nr_files',
                      help='number of states in this dimension')

    (options, args) = parser.parse_args()

    if options.nr_replicas is None:
        parser.error("You must specify the total number of replicas (--replicas). Try --help for help.")

    if options.nr_files is None:
        parser.error("You must specify the number of files to examine (--files). Try --help for help.")

    return options

    