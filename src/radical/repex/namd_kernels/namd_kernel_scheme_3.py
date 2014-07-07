"""
.. module:: radical.repex.namd_kernels.namd_kernel_scheme_3
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

class NamdKernelScheme3(NamdKernel):
    """This class is responsible for performing all operations related to NAMD for RE scheme 3.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.

    RE scheme 3:
    - Asynchronous RE scheme: MD run on target resource is overlapped with local exchange step. Thus both MD run
    and exchange step are asynchronous.  
    - Number of replicas is greater than number of allocated resources.
    - Replica simulation cycle is defined by the fixed number of simulation time-steps each replica has to perform.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed locally
    Overall algorithm is as follows:
        - First replicas in "waiting" state are submitted to pilot.
        - Then fixed time interval (cycle_time in input.json) must elapse before exchange step may take place.
        - After this fixed time interval elapsed, some replicas are still running on target resource.
        - In local exchange step are participating replicas which had finished MD run (state "finished") and
        replicas in "waiting" state.
        - After local exchanges step is performed replicas which participated in exchange are submitted to pilot
        to perform next simulation cycle
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

        for i in range(len(replicas)):
            repl_i = replicas[i]
            for j in range(len(replicas)):
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
        ps = [0.0]*(len(replicas))
  
        for j in range(len(replicas)):
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

    def check_replicas(self, replicas):
        """
        """
        finished_replicas = []
        files = os.listdir( self.work_dir_local )

        for r in replicas:
            history_name =  self.inp_basename[:-5] + "_%s_%s.history" % ( r.id, (r.cycle-1) )
            for item in files:
                if (item.startswith(history_name)):
                    if r not in finished_replicas:
                        finished_replicas.append( r )

        return finished_replicas

