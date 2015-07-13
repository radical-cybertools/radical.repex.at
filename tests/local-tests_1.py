import os
import sys
import json
import unittest
import optparse
from os import path
import radical.pilot
import radical.utils.logger as rul
from repex_utils.replica_cleanup import *
from amber_kernels_3d_tuu.kernel_pattern_b_3d_tuu import AmberKernelPatternB3dTUU
from pilot_kernels.pilot_kernel_pattern_b_multi_d import PilotKernelPatternBmultiD

class TestOutput(unittest.TestCase):

    #------------------------------------------------------------------------------------------------------
    #
    def setUp(self):

        #--------------------------------------------------------------------------------------------------

        name = 'TUU-tests'
        logger  = rul.getLogger ('radical.repex', name)

        self.work_dir_local = os.getcwd()

        # get input file
        json_data=open("config/ace_ala_nme_input_local.json")
        self.inp_file = json.load(json_data)
        json_data.close()

        # initializing kernels
        self.md_kernel = AmberKernelPatternB3dTUU( self.inp_file, self.work_dir_local )
        self.pilot_kernel = PilotKernelPatternBmultiD( self.inp_file )

        # initializing replicas
        self.replicas = self.md_kernel.initialize_replicas()

        try:
            #pilot_manager, pilot_object, session = self.pilot_kernel.launch_pilot()

            #self.pilot_kernel.run_simulation( self.replicas, pilot_object, session, self.md_kernel )

            base = self.md_kernel.inp_basename + ".mdin"

            # finally we are moving all files to individual replica directories
            move_output_files(self.work_dir_local, base, self.replicas )

            logger.info("Simulation successfully finished!")
            logger.info("Please check output files in replica_x directories.")

        except:
            logger.info("Unexpected error: {0}".format(sys.exc_info()[0]) )
            raise

        finally :
            # always clean up the session, no matter if we caught an exception or not
            logger.info("Closing session.")
            #session.close (cleanup=False)

    #------------------------------------------------------------------------------------------------------
    #
    def test_for_any_exchanges(self):
        # test if output folders exists
        for r in range(len(self.replicas)):
            r_dir = self.work_dir_local + "/replica_%d" % self.replicas[r].id
            self.assertTrue( os.path.exists(r_dir) )

    #------------------------------------------------------------------------------------------------------
    #
    def tearDown(self):
        clean_up(self.work_dir_local, self.replicas)


#------------------------------------------------------------------------------------------------------
#

if __name__ == '__main__':

    unittest.main()

