"""
.. module:: radical.repex.namd_kernels.namd_kernel_scheme_2a
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import math
import json
import random
from os import path
import radical.pilot
from kernels.kernels import KERNELS
from replicas.replica import Replica
from namd_kernels.namd_kernel import *

#-----------------------------------------------------------------------------------------------------------------------------------

class NamdKernelScheme2a(NamdKernel):
    """This class is responsible for performing all operations related to NAMD for RE scheme 2a.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.

    RE scheme 2a:
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

        NamdKernel.__init__(self, inp_file, work_dir_local)

#----------------------------------------------------------------------------------------------------------------------------------

    #compute matrix of dimension-less energies: each column is a replica 
    #and each row is a state
    #so U[i][j] is the energy of replica j in state i. 
    #
    #Note that the matrix is sized to include all of the replicas and states 
    #but the energies of replicas not 
    #in waiting state, or those of waiting replicas for states not belonging to 
    #waiting replicas list are undefined.
    # OK
    def compute_swap_matrix(self, replicas):
        """        
        """
        # init matrix
        swap_matrix = [[ 0. for j in range(self.replicas)] 
             for i in range(self.replicas)]
 
        # updating replica temperatures and energies after md run
        for r in replicas:
                # getting OLDTEMP and POTENTIAL from .history file of previous run
                old_temp, old_energy = NamdKernel.get_historical_data(self, r,(r.cycle-1))

                # updating replica temperature
                r.new_temperature = old_temp   
                r.old_temperature = old_temp   
                r.potential = old_energy

        for i in range(self.replicas):
            repl_i = replicas[i]
            for j in range(self.replicas):
                # here each column (representing replica) of U has all swappable results
                repl_j = replicas[j]
                swap_matrix[repl_j.sid][repl_i.id] = self.reduced_energy(repl_j.old_temperature,repl_i.potential)
        return swap_matrix

#----------------------------------------------------------------------------------------------------------------------------------

    def reduced_energy(self, temperature, potential):
        kb = 0.0019872041
        beta = 1. / (kb*temperature)     
        return float(beta * potential)

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

