"""
.. module:: radical.repex.amber_kernels.amber_kernel
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

#-----------------------------------------------------------------------------------------------------------------------------------

class AmberKernelScheme2(object):
    """This class is responsible for performing all operations related to Amber for RE scheme S2.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.

    RE scheme S2:
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

        self.amber_path = inp_file['input.AMBER']['amber_path']
        self.inp_basename = inp_file['input.AMBER']['input_file_basename']
        self.inp_folder = inp_file['input.AMBER']['input_folder']
        self.amber_restraints = inp_file['input.AMBER']['amber_restraints']
        self.amber_coordinates = inp_file['input.AMBER']['amber_coordinates']
        self.amber_parameters = inp_file['input.AMBER']['amber_parameters']
        self.replicas = int(inp_file['input.AMBER']['number_of_replicas'])
        self.replica_cores = int(inp_file['input.AMBER']['replica_cores'])
        self.min_temp = float(inp_file['input.AMBER']['min_temperature'])
        self.max_temp = float(inp_file['input.AMBER']['max_temperature'])
        self.cycle_steps = int(inp_file['input.AMBER']['steps_per_cycle'])
        self.work_dir_local = work_dir_local

#----------------------------------------------------------------------------------------------------------------------------------

    def gibbs_exchange(self, r_i, replicas, swap_matrix):
        """Produces a replica "j" to exchange with the given replica "i"
        based off independence sampling of the discrete distribution

        Arguments:
        r_i - given replica for which is found partner replica
        replicas - list of Replica objects
        swap_matrix - matrix of dimension-less energies, where each column is a replica 
        and each row is a state

        Returns:
        r_j - replica to exchnage parameters with
        """
        #evaluate all i-j swap probabilities
        ps = [0.0]*(self.replicas)
  
        for j in range(self.replicas):
            r_j = replicas[j]
            ps[j] = -(swap_matrix[r_i.sid][r_j.id] + swap_matrix[r_j.sid][r_i.id] - 
                      swap_matrix[r_i.sid][r_i.id] - swap_matrix[r_j.sid][r_j.id]) 

        new_ps = []
        for item in ps:
            new_item = math.exp(item)
            new_ps.append(new_item)
        ps = new_ps
        # index of swap replica within replicas_waiting list
        j = self.weighted_choice_sub(ps)
        # actual replica
        r_j = replicas[j]
        return r_j

#----------------------------------------------------------------------------------------------------------------------------------

    def weighted_choice_sub(self, weights):
        """Copy from AsyncRE code
        """

        rnd = random.random() * sum(weights)
        for i, w in enumerate(weights):
            rnd -= w
            if rnd < 0:
                return i

#-----------------------------------------------------------------------------------------------------------------------------------

    def build_input_file(self, replica):
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

        if (replica.cycle == 0):
            old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1)) 

        else:
            old_name = replica.old_path + "/%s_%d_%d" % (basename, replica.id, (replica.cycle-1))

        try:
            r_file = open( (os.path.join((self.work_dir_local + "/amber_inp/"), template)), "r")
        except IOError:
            print 'Warning: unable to access template file %s' % template

        tbuffer = r_file.read()
        r_file.close()

        tbuffer = tbuffer.replace("@nstlim@",str(self.cycle_steps))
        tbuffer = tbuffer.replace("@temp@",str(int(replica.new_temperature)))
        
        replica.cycle += 1

        try:
            w_file = open(new_input_file, "w")
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            print 'Warning: unable to access file %s' % new_input_file

#-----------------------------------------------------------------------------------------------------------------------------------

    def prepare_replicas_for_md(self, replicas, resource):
        """Prepares all replicas for execution. In this function are created CU descriptions for replicas, are
        specified input/output files to be transferred to/from target system. Note: input files for first and 
        subsequent simulation cycles are different.
        """
        compute_replicas = []
        for r in range(len(replicas)):
            self.build_input_file(replicas[r])
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
                crds = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_coordinates
                parm = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_parameters
                rstr = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_restraints


                cu.executable = self.amber_path
                cu.pre_exec = ["module load amber/12"]
                cu.mpi = True
                cu.arguments = ["-O", "-i ", input_file, "-o ", output_file, "-p ", self.amber_parameters, "-c ", self.amber_coordinates, "-r ", new_coor, "-x ", new_traj, "-inf ", new_info]
                cu.cores = 2
                cu.input_data = [input_file, crds, parm, rstr]
                cu.output_data = [new_coor, new_traj, new_info]
                compute_replicas.append(cu)
            else:
                cu = radical.pilot.ComputeUnitDescription()

                old_coor = replicas[r].old_path + "/" + self.amber_coordinates
                crds = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_coordinates
                parm = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_parameters
                rstr = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_restraints
                cu.executable = self.amber_path
                cu.pre_exec = ["module load amber/12"]
                cu.mpi = True
                cu.arguments = ["-O", "-i ", input_file, "-o ", output_file, "-p ", self.amber_parameters, "-c ", old_coor, "-r ", new_coor, "-x ", new_traj, "-inf ", new_info]
                cu.cores = 2

                cu.input_data = [input_file, crds, parm, rstr]
                cu.output_data = [new_coor, new_traj, new_info]
                compute_replicas.append(cu)

        return compute_replicas

#-----------------------------------------------------------------------------------------------------------------------------------

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
            # matrix column calculator's name is hardcoded
            calculator = self.work_dir_local + "/amber_kernels/matrix_calculator_s2.py"
            cu.input_data = [calculator]
            cu.arguments = ["matrix_calculator_s2.py", r, (replicas[r].cycle-1), len(replicas), basename]
            cu.cores = 1            
            cu.output_data = [matrix_col]
            exchange_replicas.append(cu)

        return exchange_replicas

#-----------------------------------------------------------------------------------------------------------------------------------

    def initialize_replicas(self):
        """Initializes replicas and their attributes to default values

           Changed to use geometrical progression for temperature assignment.
        """
        replicas = []
        N = self.replicas
        factor = (self.max_temp/self.min_temp)**(1./(N-1))
        for k in range(N):
            new_temp = self.min_temp * (factor**k)
            r = Replica(k, new_temp)
            replicas.append(r)
            
        return replicas

