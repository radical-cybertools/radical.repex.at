"""
.. module:: radical.repex.md_kernels.md_kernel_3d_qmmm
.. moduleauthor::  <antons.treikalis@rutgers.edu>

References:
1 - asyncre-bigjob: https://github.com/saga-project/asyncre-bigjob
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import math
import random
from os import path
import radical.pilot
from replicas.replica import Replica3d
from amber_kernels_tex.amber_kernel_tex_pattern_b import AmberKernelTexPatternB
from amber_kernels_us.amber_kernel_us_pattern_b import AmberKernelUSPatternB

#----------------------------------------------------------------------------------------------------

class MdKernel3dTUU(object):
    """
    """
    def __init__(self, inp_file,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        self.dims = 3
    
        self.resource = inp_file['input.PILOT']['resource']
        if 'number_of_cycles' in inp_file['input.MD']:
            self.nr_cycles = int(inp_file['input.MD']['number_of_cycles'])
        else:
            self.nr_cycles = None

        self.input_folder = inp_file['input.MD']['input_folder']
        self.inp_basename = inp_file['input.MD']['input_file_basename']
         
        self.amber_coordinates = inp_file['input.MD']['amber_coordinates']
        self.amber_parameters = inp_file['input.MD']['amber_parameters']
        self.amber_input = inp_file['input.MD']['amber_input']

        if 'replica_mpi' in inp_file['input.MD']:
            if inp_file['input.MD']['replica_mpi'] == "True":
                self.md_replica_mpi = True
            else:
                self.md_replica_mpi = False
        else:
            self.md_replica_mpi= False

        if 'replica_cores' in inp_file['input.MD']:
            self.md_replica_cores = int(inp_file['input.MD']['replica_cores'])
        else:
            self.md_replica_cores = 1
        
        self.cycle_steps = int(inp_file['input.MD']['steps_per_cycle'])
        self.work_dir_local = work_dir_local

        self.us_template = inp_file['input.MD']['us_template']                       
        self.current_cycle = -1

        # hardcoded for now
        self.replicas_d1 = int(inp_file['input.DIM']['umbrella_sampling_1']["number_of_replicas"])
        self.replicas_d2 = int(inp_file['input.DIM']['temperature_2']["number_of_replicas"])
        self.replicas_d3 = int(inp_file['input.DIM']['umbrella_sampling_3']["number_of_replicas"])
        
        self.replicas = self.replicas_d1 * self.replicas_d2 * self.replicas_d3 
        self.restraints_files = []
        for k in range(self.replicas):
            self.restraints_files.append(self.us_template + "." + str(k) )
 
        self.us_start_param_d1 = float(inp_file['input.DIM']['umbrella_sampling_1']['us_start_param'])
        self.us_end_param_d1 = float(inp_file['input.DIM']['umbrella_sampling_1']['us_end_param'])

        self.us_ex_cores = int(inp_file['input.DIM']['umbrella_sampling_1']['exchange_replica_cores'])
        if 'exchange_replica_mpi' in inp_file['input.DIM']['umbrella_sampling_1']:
            if inp_file['input.DIM']['umbrella_sampling_1']['exchange_replica_mpi'] == 'True':
                self.us_ex_mpi = True
            else:
                self.us_ex_mpi = False
 
        self.us_start_param_d3 = float(inp_file['input.DIM']['umbrella_sampling_3']['us_start_param'])
        self.us_end_param_d3 = float(inp_file['input.DIM']['umbrella_sampling_3']['us_end_param'])

        self.us_ex_cores = int(inp_file['input.DIM']['umbrella_sampling_3']['exchange_replica_cores'])
        if 'exchange_replica_mpi' in inp_file['input.DIM']['umbrella_sampling_3']:
            if inp_file['input.DIM']['umbrella_sampling_3']['exchange_replica_mpi'] == 'True':
                self.us_ex_mpi = True
            else:
                self.us_ex_mpi = False
        
        self.min_temp = float(inp_file['input.DIM']['temperature_2']['min_temperature'])
        self.max_temp = float(inp_file['input.DIM']['temperature_2']['max_temperature'])

        self.temp_ex_cores = int(inp_file['input.DIM']['temperature_2']['exchange_replica_cores'])
        if 'exchange_replica_mpi' in inp_file['input.DIM']['temperature_2']:
            if inp_file['input.DIM']['temperature_2']['exchange_replica_mpi'] == 'True':
                self.temp_ex_mpi = True
            else:
                self.temp_ex_mpi = False

    #---------------------------------------------------------------------------------------------------
    #
    def gibbs_exchange(self, r_i, replicas, swap_matrix):
        """Adopted from asyncre-bigjob [1]
        Produces a replica "j" to exchange with the given replica "i"
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
        ps = [0.0]*(len(replicas))

        j = 0
        for r_j in replicas:
            ps[j] = -(swap_matrix[r_i.sid][r_j.id] + swap_matrix[r_j.sid][r_i.id] - 
                           swap_matrix[r_i.sid][r_i.id] - swap_matrix[r_j.sid][r_j.id]) 
            j += 1
        
        ######################################
        new_ps = []
        for item in ps:
            new_item = math.exp(item)
            new_ps.append(new_item)
        ps = new_ps
        # index of swap replica within replicas_waiting list
        j = len(replicas)
        while j > (len(replicas) - 1):
            j = self.weighted_choice_sub(ps)
        
        # actual replica
        r_j = replicas[j]
        ######################################

        #r_j = replicas[0]
        return r_j

    #----------------------------------------------------------
    #
    def weighted_choice_sub(self, weights):
        """Adopted from asyncre-bigjob [1]
        """

        rnd = random.random() * sum(weights)
        for i, w in enumerate(weights):
            rnd -= w
            if rnd < 0:
                return i

    #----------------------------------------------------------
    # 
    def reduced_energy(self, temperature, potential):
        """Adopted from asyncre-bigjob [1]
        """
        kb = 0.0019872041
        beta = 1. / (kb*temperature)     
        return float(beta * potential)

