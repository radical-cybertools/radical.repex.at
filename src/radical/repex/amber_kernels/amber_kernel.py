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

class AmberKernel(object):
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
        try:
            self.replica_mpi = inp_file['input.AMBER']['replica_mpi']
        except:
            self.replica_mpi = False

#----------------------------------------------------------------------------------------------------------------------------------

    # ok
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

    # ok
    def weighted_choice_sub(self, weights):
        """Copy from AsyncRE code
        """

        rnd = random.random() * sum(weights)
        for i, w in enumerate(weights):
            rnd -= w
            if rnd < 0:
                return i

#-----------------------------------------------------------------------------------------------------------------------------------

    # ok
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

#-----------------------------------------------------------------------------------------------------------------------------------

    # ok
    def get_historical_data(self, replica, cycle):
        """Retrieves temperature and potential energy from simulaion output file <file_name>.history
        """

        temp = 0.0    #temperature
        eptot = 0.0   #potential
        if not os.path.exists(replica.new_history):
            print "history file %s not found" % replica.new_history
        else:
            f = open(replica.new_history)
            lines = f.readlines()
            f.close()

            for i in range(len(lines)):
                if "TEMP(K)" in lines[i]:
                    temp = float(lines[i].split()[8])
                elif "EPtot" in lines[i]:
                    eptot = float(lines[i].split()[8])

        return temp, eptot
