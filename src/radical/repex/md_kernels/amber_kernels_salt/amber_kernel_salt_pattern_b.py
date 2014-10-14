"""
.. module:: radical.repex.md_kernles.amber_kernels_salt.amber_kernel_salt_pattern_b
.. moduleauthor::  <haoyuan.chen@rutgers.edu>
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import time
import math
import json
import random
import shutil
import datetime
from os import path
import radical.pilot
from kernels.kernels import KERNELS
from replicas.replica import Replica
from amber_kernel_salt import *
import amber_kernels_salt.amber_matrix_calculator_pattern_b

#-----------------------------------------------------------------------------------------------------------------------------------

class AmberKernelSaltPatternB(AmberKernelSalt):
    """This class is responsible for performing all operations related to Amber for RE scheme S2.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.

    RE pattern B:
    - Synchronous RE scheme: none of the replicas can start exchange before all replicas has finished MD run.
    Conversely, none of the replicas can start MD run before all replicas has finished exchange step. 
    In other words global barrier is present.   
    - Number of replicas is greater than number of allocated resources for both MD and exchange step.
    - Simulation cycle is defined by the fixed number of simulation time-steps for each replica.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed in decentralized fashion on target resource.

    """
    def __init__(self, inp_file,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        AmberKernelSalt.__init__(self, inp_file, work_dir_local)

#-----------------------------------------------------------------------------------------------------------------------------------
    # OK
    def build_input_file(self, replica, shared_data_url):
        """Builds input file for replica, based on template input file ala10.mdin
        """

        basename = self.inp_basename
        template = self.inp_basename[:-5] + ".mdin"
            
        new_input_file = "%s_%d_%d.mdin" % (basename, replica.id, replica.cycle)
        outputname = "%s_%d_%d.mdout" % (basename, replica.id, replica.cycle)
        old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1))
        replica.new_coor = "%s_%d_%d.rst" % (basename, replica.id, replica.cycle)
        replica.new_traj = "%s_%d_%d.mdcrd" % (basename, replica.id, replica.cycle)
        replica.new_info = "%s_%d_%d.mdinfo" % (basename, replica.id, replica.cycle)

        if (replica.cycle == 0):
            first_step = 0
        elif (replica.cycle == 1):
            first_step = int(self.cycle_steps)
        else:
            first_step = (replica.cycle - 1) * int(self.cycle_steps)

        restraints = self.amber_restraints
        #if (replica.cycle == 0):
        #    restraints = self.amber_restraints
        #else:
            ##################################
            # changing first path from absolute 
            # to relative so that Amber can 
            # process it
            ##################################
            #path_list = []
            #for char in reversed(replica.first_path):
            #    if char == '/': break
            #    path_list.append( char )

            #modified_first_path = ''
            #for char in reversed( path_list ):
            #    modified_first_path += char

            #modified_first_path = '../' + modified_first_path.rstrip()
            #restraints = modified_first_path + "/" + self.amber_restraints

        try:
            r_file = open( (os.path.join((self.work_dir_local + "/amber_inp/"), template)), "r")
        except IOError:
            print 'Warning: unable to access template file %s' % template

        tbuffer = r_file.read()
        r_file.close()

        tbuffer = tbuffer.replace("@nstlim@",str(self.cycle_steps))
        tbuffer = tbuffer.replace("@saltcon@",str(int(replica.new_salt_concentration)))
        tbuffer = tbuffer.replace("@rstr@", restraints )
        
        replica.cycle += 1

        try:
            w_file = open(new_input_file, "w")
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            print 'Warning: unable to access file %s' % new_input_file


#-----------------------------------------------------------------------------------------------------------------------------------
    
    def prepare_shared_md_input(self):
        """Creates a Compute Unit for shared data staging in
        these are Amber input files shared between all replicas
        """

        shared_data_unit = radical.pilot.ComputeUnitDescription()

        crds = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_coordinates
        parm = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_parameters
        rstr = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_restraints

        shared_data_unit.executable = "/bin/true"
        shared_data_unit.cores = 1
        shared_data_unit.input_staging = [str(crds), str(parm)]
 
        return shared_data_unit


#-----------------------------------------------------------------------------------------------------------------------------------
    # OK
    def prepare_replicas_for_md(self, replicas, shared_data_url):
        """Prepares all replicas for execution. In this function are created CU descriptions for replicas, are
        specified input/output files to be transferred to/from target system. Note: input files for first and 
        subsequent simulation cycles are different.

        Arguments:
        replicas - list of Replica objects

        Returns:
        compute_replicas - list of radical.pilot.ComputeUnitDescription objects
        """
        compute_replicas = []
        for r in range(len(replicas)):
            # need to avoid this step!
            self.build_input_file(replicas[r], shared_data_url)
      
            # in principle restraint file should be moved to shared directory
            rstr = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_restraints

            input_file = "%s_%d_%d.mdin" % (self.inp_basename, replicas[r].id, (replicas[r].cycle-1))
            # this is not transferred back
            output_file = "%s_%d_%d.mdout" % (self.inp_basename, replicas[r].id, (replicas[r].cycle-1))

            new_coor = replicas[r].new_coor
            new_traj = replicas[r].new_traj
            new_info = replicas[r].new_info
            old_coor = replicas[r].old_coor
            old_traj = replicas[r].old_traj

            if replicas[r].cycle == 1:
                cu = radical.pilot.ComputeUnitDescription()
                cu.executable = self.amber_path
                cu.pre_exec = self.pre_exec
                cu.mpi = self.replica_mpi
                cu.arguments = ["-O", "-i ", input_file, 
                                      "-o ", output_file, 
                                      "-p ", shared_data_url + "/" + self.amber_parameters, 
                                      "-c ", shared_data_url + "/" + self.amber_coordinates, 
                                      "-r ", new_coor, 
                                      "-x ", new_traj, 
                                      "-inf ", new_info]

                cu.cores = self.replica_cores
                cu.input_staging = [str(input_file), str(rstr)]
                #cu.input_staging = [str(input_file), str(crds), str(parm), str(rstr)]
                #cu.output_staging = [str(new_coor), str(new_traj), str(new_info)]
                compute_replicas.append(cu)
            else:
                cu = radical.pilot.ComputeUnitDescription()

                #old_coor = replicas[r].old_path + "/" + self.amber_coordinates

                #crds = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_coordinates
                #parm = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_parameters
                #rstr = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_restraints

                cu.executable = self.amber_path
                cu.pre_exec = self.pre_exec
                cu.mpi = self.replica_mpi
                cu.arguments = ["-O", "-i ", input_file, 
                                      "-o ", output_file, 
                                      "-p ", shared_data_url + "/" + self.amber_parameters, 
                                      "-c ", shared_data_url + "/" + self.amber_coordinates, 
                                      "-r ", new_coor, 
                                      "-x ", new_traj, 
                                      "-inf ", new_info]

                cu.cores = self.replica_cores

                cu.input_staging = [str(input_file), str(rstr)]
                #cu.input_staging = [str(input_file), str(crds), str(parm), str(rstr)]
                #cu.output_staging = [str(new_coor), str(new_traj), str(new_info)]
                compute_replicas.append(cu)

        return compute_replicas

#-----------------------------------------------------------------------------------------------------------------------------------
    # OK
    def prepare_replicas_for_exchange(self, replicas):
        """Creates a list of ComputeUnitDescription objects for exchange step on resource.
        Number of matrix_calculator_s2.py instances invoked on resource is equal to the number 
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
            basename = self.inp_basename

            cu = radical.pilot.ComputeUnitDescription()
            cu.executable = "python"
            # each scheme has it's own calculator!
            # consider moving this in shared input data folder!
            calculator_path = os.path.dirname(amber_kernels_salt.amber_matrix_calculator_pattern_b.__file__)
            calculator = calculator_path + "/amber_matrix_calculator_pattern_b.py" 

            # in principle we can transfer this just once and use it multiple times later during the simulation
            cu.input_staging = [str(calculator)]
            cu.arguments = ["amber_matrix_calculator_pattern_b.py", r, (replicas[r].cycle-1), len(replicas), basename]
            cu.cores = 1            
            exchange_replicas.append(cu)

        return exchange_replicas




