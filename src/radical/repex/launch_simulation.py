"""
.. module:: radical.repex.namd_kernels.launch_simulation
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import math
import json
import optparse
import radical.pilot
from os import path
from replicas.replica import Replica
from namd_kernels.namd_kernel_s2 import NamdKernelS2
from pilot_kernels.pilot_kernel_s2 import PilotKernelS2

#-----------------------------------------------------------------------------------------------------------------------------------

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

#-----------------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    """Runs RE simulation using S2 scheme. 

    RE scheme S2:
    - Synchronous RE scheme: none of the replicas can start exchange before all replicas has finished MD run.
    Conversely, none of the replicas can start MD run before all replicas has finished exchange step. 
    In other words global barrier is present.   
    - Number of replicas is greater than number of allocated resources for both MD and exchange step.
    - Simulation cycle is defined by the fixed number of simulation time-steps for each replica.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed in decentralized fashion on target resource.
    """
 

    print "*********************************************************************"
    print "*                 RepEx simulation: NAMD + RE scheme S2             *"
    print "*********************************************************************"

    work_dir_local = os.getcwd()
    params = parse_command_line()
    
    # get input file
    json_data=open(params.input_file)
    inp_file = json.load(json_data)
    json_data.close()

    # initializing kernels
    md_kernel = NamdKernelS2( inp_file, work_dir_local )
    pilot_kernel = PilotKernelS2( inp_file )

    # initializing replicas
    replicas = md_kernel.initialize_replicas()
    
    session, pilot_manager, pilot_object = pilot_kernel.launch_pilot()
    
    # now we can run RE simulation
    pilot_kernel.run_simulation( replicas, session, pilot_object, md_kernel )
                
    session.close()
    
    # finally we are moving all files to individual replica directories
    md_kernel.move_output_files( replicas ) 

    # delete all replica folders
    #md_kernel.clean_up( replicas )

    #sys.exit(0)

