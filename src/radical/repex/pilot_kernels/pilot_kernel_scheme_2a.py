"""
.. module:: radical.repex.pilot_kernels.pilot_kernel_scheme_2a
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import time
import math
import json
import datetime
from os import path
import radical.pilot
from kernels.kernels import KERNELS
from pilot_kernels.pilot_kernel import *

#-----------------------------------------------------------------------------------------------------------------------------------

class PilotKernelScheme2a(PilotKernel):
    """This class is responsible for performing all Radical Pilot related operations for RE scheme 2a.
    This includes pilot launching, running main loop of RE simulation and using RP API for data staging in and out. 

    RE scheme 2a:
    - Synchronous RE scheme: none of the replicas can start exchange before all replicas has finished MD run.
    Conversely, none of the replicas can start MD run before all replicas has finished exchange step. 
    In other words global barrier is present.   
    - Number of replicas is greater than number of allocated resources for both MD and exchange step.
    - Simulation cycle is defined by the fixed number of simulation time-steps for each replica.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed locally
    """
    def __init__(self, inp_file):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        """
        PilotKernel.__init__(self, inp_file)
        
#-----------------------------------------------------------------------------------------------------------------------------------

    def run_simulation(self, replicas, pilot_object, session,  md_kernel ):
        """This function runs the main loop of RE simulation for S2 RE scheme.

        Arguments:
        replicas - list of Replica objects
        unit_manager - 
        md_kernel - an instance of NamdKernelS2 class
        """
        unit_manager = radical.pilot.UnitManager(session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(pilot_object)
        
        for i in range(self.nr_cycles):
            # returns compute objects
            compute_replicas = md_kernel.prepare_replicas(replicas, self.resource)
            submitted_replicas = unit_manager.submit_units(compute_replicas)
            unit_manager.wait_units()

            #######################################################################################
            # computing swap matrix
            swap_matrix = md_kernel.compute_swap_matrix(replicas)

            for r_i in replicas:
                r_j = md_kernel.gibbs_exchange(r_i, replicas, swap_matrix)
                if (r_j != r_i):
                    # swap temperatures                    
                    temperature = r_j.new_temperature
                    r_j.new_temperature = r_i.new_temperature
                    r_i.new_temperature = temperature
                    # record that swap was performed
                    r_i.swap = 1
                    r_j.swap = 1
            
                