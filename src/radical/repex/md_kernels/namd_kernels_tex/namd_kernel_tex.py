"""
.. module:: radical.repex.namd_kernels.namd_kernel
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
from os import path
import radical.pilot
from kernels.kernels import KERNELS
from md_kernels.md_kernel_tex import *

#-----------------------------------------------------------------------------------------------------------------------------------

class NamdKernelTex(MdKernelTex):
    """
    """
    def __init__(self, inp_file,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        MdKernelTex.__init__(self, inp_file, work_dir_local)

        try:
            self.namd_path = inp_file['input.MD']['namd_path']
        except:
            print "Using default NAMD path for %s" % inp_file['input.PILOT']['resource']
            try:
                self.namd_path = KERNELS[self.resource]["kernels"]["namd"]["executable"]
            except:
                print "NAMD path for localhost is not defined..."
        
        self.namd_structure = inp_file['input.MD']['namd_structure']
        self.namd_coordinates = inp_file['input.MD']['namd_coordinates']
        self.namd_parameters = inp_file['input.MD']['namd_parameters']
        
#----------------------------------------------------------------------------------------------------------------------------------

    def build_input_file_local(self, replica):
        """Generates input file for individual replica, based on template input file. Tokens @xxx@ are
        substituted with corresponding parameters. 
        In this function replica.cycle is incremented by one

        old_output_root @oldname@ determines which .coor .vel and .xsc files are used for next cycle

        Arguments:
        replica - a single Replica object
        """

        basename = self.inp_basename[:-5]
        template = self.inp_basename
            
        new_input_file = "%s_%d_%d.namd" % (basename, replica.id, replica.cycle)
        outputname = "%s_%d_%d" % (basename, replica.id, replica.cycle)
        old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1))
        replica.new_coor = outputname + ".coor"
        replica.new_vel = outputname + ".vel"
        replica.new_history = outputname + ".history"
        replica.new_ext_system = outputname + ".xsc" 
        historyname = replica.new_history

        replica.old_coor = old_name + ".coor"
        replica.old_vel = old_name + ".vel"
        replica.old_ext_system = old_name + ".xsc" 

        if (replica.cycle == 0):
            first_step = 0
        elif (replica.cycle == 1):
            first_step = int(self.cycle_steps)
        else:
            first_step = (replica.cycle - 1) * int(self.cycle_steps)

        old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1)) 
        structure = self.namd_structure
        coordinates = self.namd_coordinates
        parameters = self.namd_parameters

        # substituting tokens in main replica input file 
        try:
            r_file = open( (os.path.join((self.work_dir_local + "/namd_inp/"), template)), "r")
        except IOError:
            print 'Warning: unable to access template file %s' % template

        tbuffer = r_file.read()
        r_file.close()

        tbuffer = tbuffer.replace("@swap@",str(replica.swap))
        tbuffer = tbuffer.replace("@ot@",str(replica.old_temperature))
        tbuffer = tbuffer.replace("@nt@",str(replica.new_temperature))
        tbuffer = tbuffer.replace("@steps@",str(self.cycle_steps))
        tbuffer = tbuffer.replace("@rid@",str(replica.id))
        tbuffer = tbuffer.replace("@somename@",str(outputname))
        tbuffer = tbuffer.replace("@oldname@",str(old_name))
        tbuffer = tbuffer.replace("@cycle@",str(replica.cycle))
        tbuffer = tbuffer.replace("@firststep@",str(first_step))
        tbuffer = tbuffer.replace("@history@",str(historyname))
        tbuffer = tbuffer.replace("@structure@", str(structure))
        tbuffer = tbuffer.replace("@coordinates@", str(coordinates))
        tbuffer = tbuffer.replace("@parameters@", str(parameters))
        
        replica.cycle += 1
        # write out
        try:
            w_file = open( new_input_file, "w")
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            print 'Warning: unable to access file %s' % new_input_file

#-----------------------------------------------------------------------------------------------------------------------------------

    def prepare_replicas_local(self, replicas):
        """Creates a list of ComputeUnitDescription objects for MD simulation step. Here are
        specified input/output files to be transferred to/from target resource. Note: input 
        files for first and subsequent simulaition cycles are different.  

        Arguments:
        replicas - list of Replica objects

        Returns:
        compute_replicas - list of radical.pilot.ComputeUnitDescription objects
        """
        compute_replicas = []
        for r in range(len(replicas)):
            self.build_input_file_local(replicas[r])
            input_file = "%s_%d_%d.namd" % (self.inp_basename[:-5], replicas[r].id, (replicas[r].cycle-1))

            new_coor = replicas[r].new_coor
            new_vel = replicas[r].new_vel
            new_history = replicas[r].new_history
            new_ext_system = replicas[r].new_ext_system

            old_coor = replicas[r].old_coor
            old_vel = replicas[r].old_vel
            old_ext_system = replicas[r].old_ext_system 

            # only for first cycle we transfer structure, coordinates and parameters files
            if replicas[r].cycle == 1:
                cu = radical.pilot.ComputeUnitDescription()
                cu.pre_exec    = KERNELS[self.resource]["kernels"]["namd"]["pre_execution"]
                cu.executable = self.namd_path
                cu.arguments = [input_file]
                cu.cores = replicas[r].cores
                structure = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_structure
                coords = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_coordinates
                params = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_parameters
                cu.input_staging = [str(input_file), str(structure), str(coords), str(params)]
                cu.output_staging = [str(new_coor), str(new_vel), str(new_history), str(new_ext_system) ]
                compute_replicas.append(cu)
            else:
                cu = radical.pilot.ComputeUnitDescription()
                cu.pre_exec    = KERNELS[self.resource]["kernels"]["namd"]["pre_execution"]
                cu.executable = self.namd_path
                cu.arguments = [input_file]
                cu.cores = 1
                structure = self.inp_folder + "/" + self.namd_structure
                coords = self.inp_folder + "/" + self.namd_coordinates
                params = self.inp_folder + "/" + self.namd_parameters
                cu.input_staging = [str(input_file), str(structure), str(coords), str(params), str(old_coor), str(old_vel), str(old_ext_system)]
                cu.output_staging = [str(new_coor), str(new_vel), str(new_history), str(new_ext_system) ]
                compute_replicas.append(cu)

        return compute_replicas

#----------------------------------------------------------------------------------------------------------------------------------

    def get_historical_data(self, replica, cycle):
        """Retrieves temperature and potential energy from simulaion output file <file_name>.history
        """
        if not os.path.exists(replica.new_history):
            print "history file not found: "
            print replica.new_history
        else:
            f = open(replica.new_history)
            lines = f.readlines()
            f.close()
            data = lines[0].split()
         
        return float(data[0]), float(data[1])