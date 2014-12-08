"""
.. module:: radical.repex.md_kernels.md_kernel_tex
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
from replicas.replica import Replica2d

#-----------------------------------------------------------------------------------------------------------------------------------

class MdKernel2d(object):
    """
    """
    def __init__(self, inp_file,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        self.resource = inp_file['input.PILOT']['resource']
        self.inp_basename = inp_file['input.MD']['input_file_basename']
        self.inp_folder = inp_file['input.MD']['input_folder']
        self.replicas = int(inp_file['input.MD']['number_of_replicas'])
        self.min_salt = float(inp_file['input.MD']['min_salt'])
        self.max_salt = float(inp_file['input.MD']['max_salt'])
        self.min_temp = float(inp_file['input.MD']['min_temperature'])
        self.max_temp = float(inp_file['input.MD']['max_temperature'])

        #self.init_temperature = float(inp_file['input.MD']['init_temperature'])
        self.cycle_steps = int(inp_file['input.MD']['steps_per_cycle'])
        self.work_dir_local = work_dir_local
        self.min_temp = float(inp_file['input.MD']['min_temperature'])
        self.max_temp = float(inp_file['input.MD']['max_temperature'])

        try:
            self.nr_cycles = int(inp_file['input.MD']['number_of_cycles'])
        except:
            self.nr_cycles = None

        try:
            self.replica_mpi = inp_file['input.MD']['replica_mpi']
        except:
            self.replica_mpi = False

        try:
            self.replica_cores = inp_file['input.MD']['replica_cores']
        except:
            self.replica_cores = 1

#-----------------------------------------------------------------------------------------------------------------------------------

    def initialize_replicas(self):
        """Initializes replicas and their attributes to default values

        """
        replicas = []
        r_temperatures = []
        N = self.replicas
        factor = (self.max_temp/self.min_temp)**(1./(N-1))
        for k in range(N):
            new_temp = self.min_temp * (factor**k)
            r_temperatures.append(new_temp)

        r_salts = []
        for k in range(N):
            new_salt = (self.max_salt-self.min_salt)/(N-1)*k + self.min_salt
            r_salts.append(new_salt)

        self.replicas = len(r_temperatures) * len(r_salts)

        for i in range(N):
            new_temp = r_temperatures[i]
            for j in range(N):
                new_salt = r_salts[j]
                r = Replica2d((i*N + j), new_temp, new_salt)
                replicas.append(r)
            
        return replicas

#----------------------------------------------------------------------------------------------------------------------------------

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
        ps = [0.0]*(self.replicas)
  
        for r_j in replicas:
            ps[r_j.id] = -(swap_matrix[r_i.sid][r_j.id] + swap_matrix[r_j.sid][r_i.id] - 
                      swap_matrix[r_i.sid][r_i.id] - swap_matrix[r_j.sid][r_j.id]) 

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
        return r_j

#----------------------------------------------------------------------------------------------------------------------------------

    def weighted_choice_sub(self, weights):
        """Adopted from asyncre-bigjob [1]
        """

        rnd = random.random() * sum(weights)
        for i, w in enumerate(weights):
            rnd -= w
            if rnd < 0:
                return i

#----------------------------------------------------------------------------------------------------------------------------------

    def compute_swap_matrix(self, replicas):
        """Adopted from asyncre-bigjob [1]
        compute matrix of dimension-less energies: each column is a replica 
        and each row is a state so swap_matrix[i][j] is the energy of replica j 
        in state i. Note that the matrix is sized to include all of the replicas 
        and states but the energies of replicas not in waiting state, or those of 
        waiting replicas for states not belonging to waiting replicas list are 
        undefined.        
        """
        # init matrix
        swap_matrix = [[ 0. for j in range(self.replicas)] 
             for i in range(self.replicas)]

        # updating replica temperatures and energies after md run
        for r in replicas:
                # getting OLDTEMP and POTENTIAL from .history file of previous run
                old_temp, old_energy = self.get_historical_data(r,(r.cycle-1))

                # updating replica temperature
                r.new_temperature = old_temp   
                r.old_temperature = old_temp   
                r.potential = old_energy

        for i in range(len(replicas)):
            repl_i = replicas[i]
            for j in range(len(replicas)):
                # here each column (representing replica) of U has all swappable results
                repl_j = replicas[j]
                swap_matrix[repl_j.sid][repl_i.id] = self.reduced_energy(repl_j.old_temperature,repl_i.potential)
        return swap_matrix

#----------------------------------------------------------------------------------------------------------------------------------

    # OK
    def reduced_energy(self, temperature, potential):
        """Adopted from asyncre-bigjob [1]
        """
        kb = 0.0019872041
        beta = 1. / (kb*temperature)     
        return float(beta * potential)

#-----------------------------------------------------------------------------------------------------------------------------------

    def update_replica_info(self, replicas):
        """This function is primarely used by both NAMD and Amber kernels in scheme 4.
        It opens matrix_column_x_x.dat file, which is transferred back to local system
        after eachange step and reads the following data from it.

        path_to_replica_folder - remote location of replica files from previous md run
        stopped_i_run - timestep at which md run was cancelled; this is used to provide arguments
        for the next MD run
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
                r.stopped_run = int(lines[2])

                print "Setting stopped i run to: %d for replica %d" % (r.stopped_run, r.id)
            except:
                raise

#-----------------------------------------------------------------------------------------------------------------------------------
    # OK
    def exchange_params(self, replica_1, replica_2):
        salt = replica_2.new_salt_concentration
        replica_2.new_salt_concentration = replica_1.new_salt_concentration
        replica_1.new_salt_concentration = salt
