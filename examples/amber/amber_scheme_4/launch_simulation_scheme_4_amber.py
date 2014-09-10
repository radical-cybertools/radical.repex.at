"""
.. module:: radical.repex.launch_simulation_scheme_4_amber
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import json
from os import path
from repex_utils.replica_cleanup import *
from repex_utils.parser import parse_command_line
from amber_kernels_tex.amber_kernel_tex_scheme_4 import AmberKernelTexScheme4
from pilot_kernels.pilot_kernel_scheme_4 import PilotKernelScheme4

#-----------------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    """Runs RE simulation using scheme 4. 

    RE scheme 4:
    TODO...

    """
 
    print "*********************************************************************"
    print "*                RepEx simulation: AMBER + RE scheme 4              *"
    print "*********************************************************************"

    work_dir_local = os.getcwd()
    params = parse_command_line()
    
    # get input file
    json_data=open(params.input_file)
    inp_file = json.load(json_data)
    json_data.close()

    # initializing kernels
    md_kernel = AmberKernelTexScheme4( inp_file, work_dir_local )
    pilot_kernel = PilotKernelScheme4( inp_file )

    # initializing replicas
    replicas = md_kernel.initialize_replicas()

    pilot_manager, pilot_object, session = pilot_kernel.launch_pilot()
    
    # now we can run RE simulation
    pilot_kernel.run_simulation( replicas, pilot_object, session, md_kernel )

    # this is a quick hack
    base = md_kernel.inp_basename + ".mdin"

    # finally we are moving all files to individual replica directories
    move_output_files(work_dir_local, base, replicas ) 

    session.close()

