"""
.. module:: radical.repex.amber_kernels.launch_simulation_pattern_b_3d_qmmm
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import json
from os import path
import radical.pilot
import radical.utils.logger as rul
from repex_utils.replica_cleanup import *
from repex_utils.parser import parse_command_line
from amber_kernels_3d_tuu.kernel_pattern_b_3d_tuu import AmberKernelPatternB3dTUU
from pilot_kernels.pilot_kernel_pattern_b_multi_d import PilotKernelPatternBmultiD

#-----------------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    """Runs RE simulation using pattern B. 
    """

    name = 'launcher-3d-TUU'
    logger  = rul.getLogger ('radical.repex', name)

    logger.info("*********************************************************************")
    logger.info("*            RepEx simulation: AMBER + TUU + pattern B             *")
    logger.info("*********************************************************************")

    work_dir_local = os.getcwd()
    params = parse_command_line()

    # get input file
    json_data=open(params.input_file)
    inp_file = json.load(json_data)
    json_data.close()

    # initializing kernels
    md_kernel = AmberKernelPatternB3dTUU( inp_file, work_dir_local )
    pilot_kernel = PilotKernelPatternBmultiD( inp_file )

    # initializing replicas
    replicas = md_kernel.initialize_replicas()

    try:

        pilot_manager, pilot_object, session = pilot_kernel.launch_pilot()

        # now we can run RE simulation
        pilot_kernel.run_simulation( replicas, pilot_object, session, md_kernel )

        base = md_kernel.inp_basename + ".mdin"

        # finally we are moving all files to individual replica directories
        move_output_files(work_dir_local, base, replicas )

        logger.info("Simulation successfully finished!")
        logger.info("Please check output files in replica_x directories.")

    except:
        logger.info("Unexpected error: {0}".format(sys.exc_info()[0]) )
        raise

    finally :
        # always clean up the session, no matter if we caught an exception or
        # not.
       logger.info("Closing session.")
       session.close (cleanup=False)

