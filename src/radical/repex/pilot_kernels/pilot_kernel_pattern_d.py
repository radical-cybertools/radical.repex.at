"""
.. module:: radical.repex.pilot_kernels.pilot_kernel_pattern_d
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
import radical.utils.logger as rul
from pilot_kernels.pilot_kernel import *

#-----------------------------------------------------------------------------------------------------------------------------------

class PilotKernelPatternD(PilotKernel):
    """This class is responsible for performing all Radical Pilot related operations for RE scheme 4.
    This includes pilot launching, running main loop of RE simulation and using RP API for data staging in and out. 

    RE scheme 4:

    """
    def __init__(self, inp_file):
        """Constructor.

        Arguments:
        inp_file - json input file with Pilot and NAMD related parameters as specified by user 
        """
        PilotKernel.__init__(self, inp_file)

        self.name = 'pk-patternD'
        self.logger  = rul.getLogger ('radical.repex', self.name)

#-----------------------------------------------------------------------------------------------------------------------------------

    def compose_swap_matrix(self, replicas):
        """Creates a swap matrix from matrix_column_x.dat files. 
        matrix_column_x.dat - is populated on targer resource and then transferred back. This
        file is created for each replica and has data for one column of swap matrix. In addition to that,
        this file holds path to pilot compute unit of the previous run, where reside NAMD output files for 
        a given replica. 

        Arguments:
        replicas - list of Replica objects

        Returns:
        swap_matrix - 2D list of lists of dimension-less energies, where each column is a replica 
        and each row is a state
        """
        base_name = "matrix_column"
 
        # init matrix
        swap_matrix = [[ 0. for j in range(len(replicas))] 
             for i in range(len(replicas))]

        for r in replicas:
            column_file = base_name + "_" + str(r.id) + "_" + str(r.cycle-1) + ".dat"       
            try:
                f = open(column_file)
                lines = f.readlines()
                f.close()
                data = lines[0].split()
                # populating one column at a time
                for i in range(len(replicas)):
                    swap_matrix[i][r.id] = float(data[i])

            except:
                raise

        return swap_matrix

#-----------------------------------------------------------------------------------------------------------------------------------

    def run_simulation(self, replicas, pilot_object, session,  md_kernel ):
        """This function runs the main loop of RE simulation for RE scheme 2a.

        Arguments:
        replicas - list of Replica objects
        pilot_object - radical.pilot.ComputePilot object
        session - radical.pilot.session object, the *root* object for all other RADICAL-Pilot objects 
        md_kernel - an instance of NamdKernelScheme2a class
        """

        # --------------------------------------------------------------------------
        #
        def unit_state_change_cb(unit, state):
            """This is a callback function. It gets called very time a ComputeUnit changes its state.
            """
            if unit:
                self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )

                if state == radical.pilot.states.FAILED:
                    self.logger.error("Log: {0:s}".format( unit.as_dict() ) )

        # --------------------------------------------------------------------------
  
        unit_manager = radical.pilot.UnitManager(session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(pilot_object)

        while (pilot_object.state != 'Active'):
            print "Waiting for Pilot to become active..."
            time.sleep(2)

        print "Pilot is now active..."

        for i in range(md_kernel.nr_cycles):
            print "Performing cycle: %s" % (i+1)
            print "Preparing %d replicas for MD run" % md_kernel.replicas
            compute_replicas = md_kernel.prepare_replicas_for_md(replicas)
            print "Submitting %d replicas for MD run" % md_kernel.replicas
            submitted_replicas = unit_manager.submit_units(compute_replicas)
            cycle_start = datetime.datetime.utcnow()

            # measuring cycle time as wall clock time
            cycle_stop = cycle_start
            while ( (cycle_stop - cycle_start).total_seconds() < md_kernel.cycle_time ):
                print "Cycle time has not elapsed yet..."
                time.sleep(1)
                cycle_stop = datetime.datetime.utcnow()
            print "Cycle time has elapsed, stopping replicas..."

            # sanity check
            for s_replica in submitted_replicas:
                while (s_replica.state != 'Executing'):
                    print "Waiting for Compute Unit (Replica) %s to start execution (state is: %s)" % (s_replica.uid, s_replica.state) 
                    time.sleep(1)

            for s_replica in submitted_replicas:
                # replica is now cancelled
                s_replica.cancel()

            for s_replica in submitted_replicas:
                s_replica.wait(radical.pilot.states.CANCELED)

            # this is not done for the last cycle
            if (i != (md_kernel.nr_cycles-1)):
                time.sleep(5)
                #####################################################################
                # computing swap matrix
                #####################################################################
                print "Preparing %d replicas for Exchange run" % md_kernel.replicas
                exchange_replicas = md_kernel.prepare_replicas_for_exchange(replicas)
                print "Submitting %d replicas for Exchange run" % md_kernel.replicas
                submitted_replicas = unit_manager.submit_units(exchange_replicas)
                unit_manager.wait_units()

                #####################################################################
                # compose swap matrix from individual files
                #####################################################################
                print "Composing swap matrix from individual files for all replicas"
                swap_matrix = self.compose_swap_matrix(replicas)
                md_kernel.update_replica_info(replicas)
            
                print "Performing exchange"
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
