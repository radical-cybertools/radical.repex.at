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

    def setUp(self):
        json_data=open("config/input.json")
        self.inp_file = json.load(json_data)
        json_data.close()

        self.workdir = str(self.inp_file['input.NAMD']['work_dir_local'])
        r_config = "file://localhost" + self.workdir + "/config/xsede.json"
        self.cycles = int(self.inp_file['input.PILOT']['number_of_cycles'])
        ################################################## 
        # repex stuff        

        self.md_kernel = namdKernel( self.inp_file )
        self.pilot_kernel = pilotKernel( self.inp_file, r_config )

        self.replicas = self.md_kernel.initialize_replicas()
        self.session, self.pilot_manager, self.pilot_object = self.pilot_kernel.launch_pilot()

        self.pilot_kernel.run_simulation( self.replicas, self.session, self.pilot_object, self.md_kernel )
        self.md_kernel.move_output_files( self.replicas ) 

    def test_folder_existance(self):
        # test if output folders exists
        for r in range(len(self.replicas)):
            r_dir = self.workdir + "/replica_%d" % self.replicas[r].id
            self.assertTrue( os.path.exists(r_dir) )

    def test_file_existance(self):
        # test for existance of output files 
        base_name = str(self.inp_file['input.NAMD']['input_file_basename'])
        for r in range(len(self.replicas)):
            r_dir = self.workdir + "/replica_%d" % self.replicas[r].id
            base_file = r_dir + "/" + base_name[:-5]

            for cycle in range( int(self.cycles) ):    
                namd_file = base_file + "_%s_%s.namd" % ( self.replicas[r].id, cycle )
                self.assertTrue( os.path.isfile(namd_file) )

                coor_file = base_file + "_%s_%s_out.coor" % ( self.replicas[r].id, cycle )
                self.assertTrue( os.path.isfile(coor_file) )

                vel_file = base_file + "_%s_%s_out.vel" % ( self.replicas[r].id, cycle )
                self.assertTrue( os.path.isfile(vel_file) )

                xsc_file = base_file + "_%s_%s_out.xsc" % ( self.replicas[r].id, cycle )
                self.assertTrue( os.path.isfile(vel_file) )

                history_file = base_file + "_%s_%s_out.history" % ( self.replicas[r].id, cycle )
                self.assertTrue( os.path.isfile(history_file) )

    def tearDown(self):
        self.md_kernel.clean_up( self.replicas )

def main():
    unittest.main()

if __name__ == '__main__':
    main()


