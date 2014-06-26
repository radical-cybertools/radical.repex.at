"""
.. module:: radical.repex.namd_kernels.launch_simulation_scheme_3
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import json
from os import path
import radical.pilot
from replicas.replica import Replica
from repex_utils.replica_cleanup import *
from repex_utils.parser import parse_command_line
from namd_kernels.namd_kernel_scheme_3 import NamdKernelScheme3
from pilot_kernels.pilot_kernel_scheme_3 import PilotKernelScheme3

#-----------------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    """Runs RE simulation using scheme 3. 

    RE scheme 3:
    - Asynchronous RE scheme: MD run on target resource is overlapped with local exchange step. Thus both MD run
    and exchange step are asynchronous.  
    - Number of replicas is greater than number of allocated resources.
    - Replica simulation cycle is defined by the fixed number of simulation time-steps each replica has to perform.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed locally
    Overall algorithm is as follows:
        - First replicas in "waiting" state are submitted to pilot.
        - Then fixed time interval (cycle_time in input.json) must elapse before exchange step may take place.
        - After this fixed time interval elapsed, some replicas are still running on target resource.
        - In local exchange step are participating replicas which had finished MD run (state "finished") and
        replicas in "waiting" state.
        - After local exchanges step is performed replicas which participated in exchange are submitted to pilot
        to perform next simulation cycle    
    """
 
    print "*********************************************************************"
    print "*                 RepEx simulation: NAMD + RE scheme 3              *"
    print "*********************************************************************"

    work_dir_local = os.getcwd()
    params = parse_command_line()
    
    # get input file
    json_data=open(params.input_file)
    inp_file = json.load(json_data)
    json_data.close()

    # initializing kernels
    md_kernel = NamdKernelScheme3( inp_file, work_dir_local )
    pilot_kernel = PilotKernelScheme3( inp_file )

    # initializing replicas
    replicas = md_kernel.initialize_replicas()
    
    pilot_manager, pilot_object, session = pilot_kernel.launch_pilot()
    
    # now we can run RE simulation
    pilot_kernel.run_simulation( replicas, pilot_object, session, md_kernel )
                
    # finally we are moving all files to individual replica directories
    move_output_files(work_dir_local, md_kernel.inp_basename, replicas ) 

    session.close()
    # delete all replica folders
    #clean_up(work_dir_local, replicas )

    #sys.exit(0)

