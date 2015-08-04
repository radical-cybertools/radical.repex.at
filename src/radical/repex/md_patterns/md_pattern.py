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
#from radical.ensemblemd.patterns.replica_exchange import ReplicaExchange

#-------------------------------------------------------------------------------

class MdPattern(object):
    """
    """
    def __init__(self, inp_file,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        # MOVE UP!!!!!!!!! (2d)
        #self.min_salt = float(inp_file['input.MD']['min_salt'])
        #self.max_salt = float(inp_file['input.MD']['max_salt'])
        #self.min_temp = float(inp_file['input.MD']['min_temperature'])
        #self.max_temp = float(inp_file['input.MD']['max_temperature'])
        ###########################################################

        # MOVE UP!!!!!!!!! (SALT CONCENTRATION)
        #self.min_salt = float(inp_file['input.MD']['min_salt'])
        #self.max_salt = float(inp_file['input.MD']['max_salt'])
        #self.init_temperature = float(inp_file['input.MD']['init_temperature'])
        ###########################################################
        
        #self.resource = inp_file['input.PILOT']['resource']
        self.inp_basename = inp_file['input.MD']['input_file_basename']
        self.inp_folder = inp_file['input.MD']['input_folder']
        self.replicas = int(inp_file['input.MD']['number_of_replicas'])
        self.cycle_steps = int(inp_file['input.MD']['steps_per_cycle'])
        self.work_dir_local = work_dir_local
        self.nr_cycles = int(inp_file['input.MD']['number_of_cycles'])
       
        try:
            self.replica_mpi = inp_file['input.MD']['replica_mpi']
        except:
            self.replica_mpi = False
        try:
            self.replica_cores = inp_file['input.MD']['replica_cores']
        except:
            self.replica_cores = 1

        #super(MdPattern, self).__init__()
    
    """
    #---------------------------------------------------------------------------
    # former gibbs_exchange
    def exchange(self, r_i, replicas, swap_matrix):
        
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

    #---------------------------------------------------------------------------
    #
    def weighted_choice_sub(self, weights):

        rnd = random.random() * sum(weights)
        for i, w in enumerate(weights):
            rnd -= w
            if rnd < 0:
                return i

    # not needed!!!
    def get_swap_matrix(self, replicas, matrix_columns):
 
        # init matrix
        swap_matrix = [[ 0. for j in range(len(replicas))] 
             for i in range(len(replicas))]

        matrix_columns = sorted(matrix_columns)

        for r in replicas:
            # populating one column at a time
            for i in range(len(replicas)):
                swap_matrix[i][r.id] = float(matrix_columns[r.id][i])

            # setting old_path and first_path for each replica
            if ( r.cycle == 1 ):
                r.first_path = matrix_columns[r.id][len(replicas)]
                r.old_path = matrix_columns[r.id][len(replicas)]
            else:
                r.old_path = matrix_columns[r.id][len(replicas)]

        return swap_matrix

    #---------------------------------------------------------------------------
    # 
    def reduced_energy(self, temperature, potential):
        kb = 0.0019872041
        beta = 1. / (kb*temperature)     
        return float(beta * potential)

    #---------------------------------------------------------------------------
    #
    def build_swap_matrix(self, replicas):

        base_name = "matrix_column"
        size = len(replicas)

        # init matrix
        swap_matrix = [[ 0. for j in range(size)]
             for i in range(size)]

        for r in replicas:
            column_file = base_name + "_" + str(r.cycle-1) + "_" + str(r.id) +  ".dat"       
            try:
                f = open(column_file)
                lines = f.readlines()
                f.close()
                data = lines[0].split()
                # populating one column at a time
                for i in range(size):
                    swap_matrix[i][r.id] = float(data[i])

                # setting old_path and first_path for each replica
                if ( r.cycle == 1 ):
                    r.first_path = str(data[size])
                    r.old_path = str(data[size])
                else:
                    r.old_path = str(data[size])
            except:
                raise

        return swap_matrix
    """