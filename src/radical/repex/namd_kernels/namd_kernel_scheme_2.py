"""
.. module:: radical.repex.namd_kernels.namd_kernel_scheme_2
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

#-----------------------------------------------------------------------------------------------------------------------------------

class NamdKernelScheme2(object):
    """This class is responsible for performing all operations related to NAMD for RE scheme 2.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.

    RE scheme 2:
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

        try:
            self.namd_path = inp_file['input.NAMD']['namd_path']
        except:
            print "Using default NAMD path for %s" % inp_file['input.PILOT']['resource']
            resource = inp_file['input.PILOT']['resource']
            self.namd_path = KERNELS[resource]["kernels"]["namd"]["executable"]
        self.inp_basename = inp_file['input.NAMD']['input_file_basename']
        self.inp_folder = inp_file['input.NAMD']['input_folder']
        self.namd_structure = inp_file['input.NAMD']['namd_structure']
        self.namd_coordinates = inp_file['input.NAMD']['namd_coordinates']
        self.namd_parameters = inp_file['input.NAMD']['namd_parameters']
        self.replicas = int(inp_file['input.NAMD']['number_of_replicas'])
        self.replica_cores = int(inp_file['input.NAMD']['replica_cores'])
        self.min_temp = float(inp_file['input.NAMD']['min_temperature'])
        self.max_temp = float(inp_file['input.NAMD']['max_temperature'])
        self.cycle_steps = int(inp_file['input.NAMD']['steps_per_cycle'])
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
        replica.new_coor = outputname + ".coor"
        replica.new_vel = outputname + ".vel"
        replica.new_history = outputname + ".history"
        replica.new_ext_system = outputname + ".xsc" 
        historyname = replica.new_history

        if (replica.cycle == 0):
            first_step = 0
        elif (replica.cycle == 1):
            first_step = int(self.cycle_steps)
        else:
            first_step = (replica.cycle - 1) * int(self.cycle_steps)

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

    def prepare_replicas_for_md(self, replicas, resource):
        """Creates a list of ComputeUnitDescription objects for MD simulation step. Here are
        specified input/output files to be transferred to/from target resource. Note: input 
        files for first and subsequent simulaition cycles are different.  

        Arguments:
        replicas - list of Replica objects
        resource - target resource identifier

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
                cu.pre_exec    = KERNELS[resource]["kernels"]["namd"]["pre_execution"]
                cu.executable = self.namd_path
                cu.arguments = [input_file]
                cu.cores = replicas[r].cores
                cu.mpi = False
                structure = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_structure
                coords = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_coordinates
                params = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_parameters
                cu.input_data = [input_file, structure, coords, params]
                # in principle it is not required to transfer simulation output files in order to 
                # continue next cycle; this is done mainly to have these files on local system;
                # an alternative approach would be to transfer all the files at the end of the simulation   
                cu.output_data = [new_coor, new_vel, new_history, new_ext_system ]
                compute_replicas.append(cu)
            else:
                cu = radical.pilot.ComputeUnitDescription()
                cu.pre_exec    = KERNELS[resource]["kernels"]["namd"]["pre_execution"]
                cu.executable = self.namd_path
                cu.arguments = [input_file]
                cu.cores = replicas[r].cores
                cu.mpi = False
                structure = self.inp_folder + "/" + self.namd_structure
                coords = self.inp_folder + "/" + self.namd_coordinates
                params = self.inp_folder + "/" + self.namd_parameters
                cu.input_data = [input_file]
                # in principle it is not required to transfer simulation output files in order to 
                # perform the next cycle; this is done mainly to have these files on local system;
                # an alternative approach would be to transfer all the files at the end of the simulation
                cu.output_data = [new_coor, new_vel, new_history, new_ext_system ]
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
            calculator = self.work_dir_local + "/namd_kernels/matrix_calculator_scheme_2.py"
            cu.input_data = [calculator]
            cu.arguments = ["matrix_calculator_scheme_2.py", r, (replicas[r].cycle-1), len(replicas), basename]
            cu.cores = 1            
            cu.output_data = [matrix_col]
            exchange_replicas.append(cu)

        return exchange_replicas
            
#-----------------------------------------------------------------------------------------------------------------------------------

    def initialize_replicas(self):
        """Initializes replicas and their attributes to default values.

        Returns:
        replicas - list of Replica objects
        """
        replicas = []
        for k in range(self.replicas):
            # may consider to change this    
            new_temp = random.uniform(self.max_temp , self.min_temp) * 0.8
            r = Replica(k, new_temp, self.replica_cores)
            replicas.append(r)
            
        return replicas


