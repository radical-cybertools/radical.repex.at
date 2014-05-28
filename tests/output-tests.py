import os
import sys
import time
import math
import json
import optparse
import datetime
import radical.pilot
import random
import shutil
import unittest
import os.path
import re_module
from re_module.radical_re_namd import Replica as Replica
from re_module.radical_re_namd import RepEx_NamdKernel as namdKernel
from re_module.radical_re_namd import RepEx_PilotKernel as pilotKernel

class TestOutput(unittest.TestCase):

    def test_folder_existance(self):

        json_data=open("config/input.json")
        inp_file = json.load(json_data)
        json_data.close()

        workdir = str(inp_file['input.NAMD']['work_dir_local'])
        r_config = "file://localhost" + workdir + "/config/xsede.json"
        cycles = int(inp_file['input.PILOT']['number_of_cycles'])
        ################################################## 
        # repex stuff        

        md_kernel = namdKernel( inp_file )
        pilot_kernel = pilotKernel( inp_file, r_config )

        replicas = md_kernel.initialize_replicas()
        session, pilot_manager, pilot_object = pilot_kernel.launch_pilot()

        pilot_kernel.run_simulation( replicas, session, pilot_object, md_kernel )
        md_kernel.move_output_files( replicas ) 
        ##################################################
        # test if output folders exists
        for r in range(len(replicas)):
            r_dir = workdir + "/replica_%d" % replicas[r].id
            self.assertTrue( os.path.exists(r_dir) )

        # test for existance of output files 
        base_name = str(inp_file['input.NAMD']['input_file_basename'])
        for r in range(len(replicas)):
            r_dir = workdir + "/replica_%d" % replicas[r].id
            base_file = r_dir + "/" + base_name[:-5]

            for cycle in range( int(cycles) ):    
                namd_file = base_file + "_%s_%s.namd" % ( replicas[r].id, cycle )
                self.assertTrue( os.path.isfile(namd_file) )

                coor_file = base_file + "_%s_%s_out.coor" % ( replicas[r].id, cycle )
                self.assertTrue( os.path.isfile(coor_file) )

                vel_file = base_file + "_%s_%s_out.vel" % ( replicas[r].id, cycle )
                self.assertTrue( os.path.isfile(vel_file) )

                xsc_file = base_file + "_%s_%s_out.xsc" % ( replicas[r].id, cycle )
                self.assertTrue( os.path.isfile(vel_file) )

                history_file = base_file + "_%s_%s_out.history" % ( replicas[r].id, cycle )
                self.assertTrue( os.path.isfile(history_file) )

def main():
    unittest.main()

if __name__ == '__main__':
    main()


