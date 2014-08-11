"""
.. module:: radical.repex.namd_kernels.namd_kernel_scheme_4
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
from os import path
import radical.pilot
from kernels.kernels import KERNELS
from namd_kernel_tex import *

#-----------------------------------------------------------------------------------------------------------------------------------

class NamdKernelTexScheme4(NamdKernelTex):
    """This class is responsible for performing all operations related to NAMD for RE scheme 2.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.

    RE scheme 4:


    """
    def __init__(self, inp_file, work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """
        NamdKernelTex.__init__(self, inp_file, work_dir_local)

        try:
            self.cycle_time = int(inp_file['input.MD']['cycle_time'])
        except:
            self.cycle_time = 5

        self.stopped_run = 0

#----------------------------------------------------------------------------------------------------------------------------------

    def build_input_file(self, replica):
        """Generates input file for individual replica, based on template input file. Tokens @xxx@ are
        substituted with corresponding parameters. 

        old_output_root @oldname@ determines which .coor .vel and .xsc files are used for next cycle

        Arguments:
        replica - a single Replica object
        """

        basename = self.inp_basename[:-5]
        template = self.inp_basename
            
        new_input_file = "%s_%d_%d.namd" % (basename, replica.id, replica.cycle)
        outputname = "%s_%d_%d" % (basename, replica.id, replica.cycle)
        old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1))

        # these are required to transfer outputs back to laptop, but
        # we don't know at which i_run md was stopped, so in principle
        # we can only transfer during the exchange run using calculator
        #replica.new_coor = outputname + ".coor"
        #replica.new_vel = outputname + ".vel"
        #replica.new_ext_system = outputname + ".xsc"

        # not sure if current use of first time step makes a lot of sense
        # why first step needs to be incremented???
        if (replica.cycle == 0):
            first_step = 0
        elif (replica.cycle == 1):
            first_step = int(self.cycle_steps)
        else:
            first_step = (replica.cycle - 1) * int(self.cycle_steps)

        # if, else below seems OK
        if (replica.cycle == 0):
            old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1)) 
            structure = self.namd_structure
            coordinates = self.namd_coordinates
            parameters = self.namd_parameters
        else:
            old_name = replica.old_path + "/%s_%d_%d" % (basename, replica.id, (replica.cycle-1))
            structure = replica.first_path + "/" + self.namd_structure
            coordinates = replica.first_path + "/" + self.namd_coordinates
            parameters = replica.first_path + "/" + self.namd_parameters

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
        tbuffer = tbuffer.replace("@structure@", str(structure))
        tbuffer = tbuffer.replace("@coordinates@", str(coordinates))
        tbuffer = tbuffer.replace("@parameters@", str(parameters))

        tbuffer = tbuffer.replace("@stopped_run@", str(self.stopped_run))
        
        replica.cycle += 1
        # write out
        try:
            w_file = open( new_input_file, "w")
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            print 'Warning: unable to access file %s' % new_input_file

#-----------------------------------------------------------------------------------------------------------------------------------

    def prepare_replicas_for_md(self, replicas):
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
            self.build_input_file(replicas[r])
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
                cu.mpi = False
                structure = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_structure
                coords = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_coordinates
                params = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_parameters
                cu.input_data = [input_file, structure, coords, params]
 
                #cu.output_data = [new_coor, new_vel, new_history, new_ext_system ]
                compute_replicas.append(cu)
            else:
                cu = radical.pilot.ComputeUnitDescription()
                cu.pre_exec    = KERNELS[self.resource]["kernels"]["namd"]["pre_execution"]
                cu.executable = self.namd_path
                cu.arguments = [input_file]
                cu.cores = replicas[r].cores
                cu.mpi = False
                cu.input_data = [input_file]
                # in principle it is not required to transfer simulation output files in order to 
                # perform the next cycle; this is done mainly to have these files on local system;
                # an alternative approach would be to transfer all the files at the end of the simulation

                # later we need to transfer these files back to laptop
                #cu.output_data = [new_coor, new_vel, new_history, new_ext_system ]
                compute_replicas.append(cu)

        return compute_replicas

#-----------------------------------------------------------------------------------------------------------------------------------

    def prepare_replicas_for_exchange(self, replicas):
        """Creates a list of ComputeUnitDescription objects for exchange step on resource.
        Number of matrix_calculator_scheme_2.py instances invoked on resource is equal to the number 
        of replicas. 

        Arguments:
        replicas - list of Replica objects

        Returns:
        exchange_replicas - list of radical.pilot.ComputeUnitDescription objects
        """

        exchange_replicas = []
        for r in range(len(replicas)):
           
            # name of the file which contains swap matrix column data for each replica
            matrix_col = "matrix_column_%s_%s.dat" % (r, (replicas[r].cycle-1))
            basename = self.inp_basename[:-5]
            cu = radical.pilot.ComputeUnitDescription()
            cu.executable = "python"
            # matrix column calculator's name is hardcoded
            calculator = self.work_dir_local + "/md_kernels/namd_kernels_tex/namd_matrix_calculator_scheme_4.py"
            cu.input_data = [calculator]
            cu.arguments = ["namd_matrix_calculator_scheme_4.py", r, (replicas[r].cycle-1), len(replicas), basename]
            cu.cores = 1            
            cu.output_data = [matrix_col]
            exchange_replicas.append(cu)

        return exchange_replicas

#-----------------------------------------------------------------------------------------------------------------------------------

    def update_replica_info(self, replicas):
        """
        todo...
        """
        base_name = "matrix_column"
 
        for r in replicas:
            column_file = base_name + "_" + str(r.id) + "_" + str(r.cycle-1) + ".dat"       
            try:
                f = open(column_file)
                lines = f.readlines()
                f.close()
                
                # setting old_path and first_path for each replica
                if ( r.cycle == 1 ):
                    r.first_path = lines[1]
                    r.old_path = lines[1]
                else:
                    r.old_path = lines[1]

                # setting stopped_i_run
                r.stopped_run = lines[2]
            except:
                raise

        