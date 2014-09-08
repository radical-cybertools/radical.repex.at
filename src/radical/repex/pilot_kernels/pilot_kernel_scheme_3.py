"""
.. module:: radical.repex.pilot_kernels.pilot_kernel_scheme_3
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
from pilot_kernels.pilot_kernel import *


#-----------------------------------------------------------------------------------------------------------------------------------

class PilotKernelScheme3(PilotKernel):
    """This class is responsible for performing Radical Pilot related operations for RE scheme 3.
    This includes pilot launching, running main loop of RE simulation and using RP API for data staging in and out. 

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
    def __init__(self, inp_file):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        """
        PilotKernel.__init__(self, inp_file)

        try:
            self.cycle_time = inp_file['input.MD']['cycle_time']
        except:
            print "Using default cycle time: 1 minute"
            self.cycle_time = 60
        self.cycle_time = int(self.cycle_time)
        self.simulation_time = self.runtime - 5

#-----------------------------------------------------------------------------------------------------------------------------------

    def run_simulation(self, replicas, pilot_object, session,  md_kernel ):
        """This function runs the main loop of RE simulation for RE scheme 3.

        Arguments:
        replicas - list of Replica objects
        pilot_object - radical.pilot.ComputePilot object
        session - radical.pilot.Session object, the *root* object for all other RADICAL-Pilot objects 
        md_kernel - an instance of NamdKernelScheme3 class
        """
        unit_manager = radical.pilot.UnitManager(session=session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(pilot_object)

        # making sure that pilot is running
        current_state = pilot_object.state
        while current_state != 'Active':
            print "pilot state: %s" % current_state
            time.sleep(5)
            current_state = pilot_object.state

        sim_start = datetime.datetime.utcnow()
        runtime = 0.0

        running_replicas = []
        while (runtime < (self.simulation_time * 60.0)):
            ####################################################
            for r in replicas:
                if r.state == 'I':
                    r.state = 'W'

            replicas_to_pilot = []
            for r in replicas:
                if r.state == 'W':
                    replicas_to_pilot.append(r)

            # after this call replica.cycle gets incremented by one
            if (len(replicas_to_pilot) != 0):
                print "Preparing %d replicas..." % len(replicas_to_pilot)
                compute_replicas = md_kernel.prepare_replicas_local(replicas_to_pilot)
                print "Submitting %d replicas..." % len(compute_replicas)
                submitted_replicas = unit_manager.submit_units(compute_replicas)

                for r in replicas_to_pilot:
                    r.state = 'R'

            running_replicas = running_replicas + replicas_to_pilot

            print "Start sleep..."
            time.sleep( self.cycle_time )
            print "Stop sleep..."


            print "Checking if replicas has finished..."
            replicas_finished = []
            while not replicas_finished:
                # check if replica finished
                replicas_finished = md_kernel.check_replicas( running_replicas )
                print "%d replicas has finished..." % len(replicas_finished)
                time.sleep(1)

            for r in running_replicas:
                for r_f in replicas_finished:
                    if r.id == r_f.id:
                        running_replicas.remove(r)

            print "Updating replica state..."
            for r in replicas_finished:
                r.state = 'F'

            replicas_for_exchange = []
            for r in replicas:
                if (r.state == 'W') or (r.state == 'F'):
                    replicas_for_exchange.append(r)

            print "Computing swap matrix for %d replicas..." % len(replicas_for_exchange)
            # computing swap matrix
            swap_matrix = md_kernel.compute_swap_matrix( replicas_for_exchange )

            print "Performing exchange..."
            for r_i in replicas_for_exchange:
                r_j = md_kernel.gibbs_exchange(r_i, replicas_for_exchange, swap_matrix)
                if (r_j != r_i):
                    # swap temperatures                    
                    temperature = r_j.new_temperature
                    r_j.new_temperature = r_i.new_temperature
                    r_i.new_temperature = temperature
                    # record that swap was performed
                    r_i.swap = 1
                    r_j.swap = 1

            for r in replicas_for_exchange:
                r.state = 'W'
            ####################################################
            check_point = datetime.datetime.utcnow()
            runtime = (check_point - sim_start).total_seconds()


