"""
.. module:: radical.repex.amber_kernels.launch_simulation_amber
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import json
from os import path
from amber_tex.amber_tex import *
from repex_utils.replica_cleanup import *
from radical.ensemblemd import EnsemblemdError
from repex_utils.parser import parse_command_line
from radical.ensemblemd import SingleClusterEnvironment


#-----------------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    """Runs RE simulation using Pattern-B. 

    RE Pattern-B:
    - Synchronous RE - none of the replicas can start exchange before all replicas has finished MD run.
    Conversely, none of the replicas can start MD run before all replicas has finished exchange step. 
    In other words global barrier is present.   
    - Number of replicas is greater than number of allocated resources for both MD and exchange step.
    - Simulation cycle is defined by the fixed number of simulation time-steps for each replica.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed in decentralized fashion on target resource.
    """
 
    print "*********************************************************************"
    print "*              RepEx simulation: AMBER + RE Pattern-B               *"
    print "*********************************************************************"

    try:
        work_dir_local = os.getcwd()
        params = parse_command_line()
    
        # get input file
        json_data=open(params.input_file)
        inp_file = json.load(json_data)
        json_data.close()

        # Create a new static execution context with one resource and a fixed
        # number of cores and runtime.
        cluster = SingleClusterEnvironment(
            resource=inp_file['input.PILOT']['resource'],
            cores=int(inp_file['input.PILOT']['cores']),
            walltime=int(inp_file['input.PILOT']['runtime']),
            username=inp_file['input.PILOT']['username'], 
            allocation=inp_file['input.PILOT']['project'],
            #cleanup=inp_file['input.PILOT']['cleanup']
        )

        # creating pattern object
        re_pattern = AmberTex(inp_file, work_dir_local)

        # initializing replica objects
        replicas = re_pattern.initialize_replicas()

        re_pattern.add_replicas( replicas )

        # run RE simulation  
        cluster.run(re_pattern, force_plugin="replica_exchange.static_pattern_2")


        #############################################################################
        # initializing kernels
        #md_kernel = AmberKernelTexScheme2( inp_file, work_dir_local )
        #pilot_kernel = PilotKernelScheme2( inp_file )

        # initializing replicas
        #replicas = md_kernel.initialize_replicas()

        #pilot_manager, pilot_object, session = pilot_kernel.launch_pilot()
    
        # now we can run RE simulation
        #pilot_kernel.run_simulation( replicas, pilot_object, session, md_kernel )
        #############################################################################


        # this is a quick hack
        base = md_kernel.inp_basename + ".mdin"

        # finally we are moving all files to individual replica directories
        move_output_files(work_dir_local, base, replicas ) 
        session.close(cleanup=False)

        print "Simulation successfully finished!"
        print "Please check output files in replica_x directories."

    except:
        print "Unexpected error:", sys.exc_info()[0]
        raise
    