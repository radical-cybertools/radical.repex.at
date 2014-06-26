"""
.. module:: radical.repex.pilot_kernels.pilot_kernel_scheme_2
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

class PilotKernelScheme2(PilotKernel):
    """This class is responsible for performing all Radical Pilot related operations for RE scheme 2.
    This includes pilot launching, running main loop of RE simulation and using RP API for data staging in and out. 

    RE scheme 2:
    - Synchronous RE scheme: none of the replicas can start exchange before all replicas has finished MD run.
    Conversely, none of the replicas can start MD run before all replicas has finished exchange step. 
    In other words global barrier is present.   
    - Number of replicas is greater than number of allocated resources for both MD and exchange step.
    - Simulation cycle is defined by the fixed number of simulation time-steps for each replica.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed in decentralized fashion on target resource.
    """
    def __init__(self, inp_file):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        """
        PilotKernel.__init__(self, inp_file)

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

                # setting old_path and first_path for each replica
                # 
                print "IMPORTANT: replica cycle: %d" % r.cycle
                if ( r.cycle == 1 ):
                    r.first_path = lines[1]
                    r.old_path = lines[1]
                else:
                    r.old_path = lines[1]
            except:
                raise

        return swap_matrix

#-----------------------------------------------------------------------------------------------------------------------------------

    def run_simulation(self, replicas, pilot_object, session,  md_kernel ):
        """This function runs the main loop of RE simulation for S2 RE scheme.

        Arguments:
        replicas - list of Replica objects
        unit_manager - 
        md_kernel - an instance of NamdKernelS2 class
        """
        total_cycle_times = []

        processed_unit_ids = []
        md_cycle_execution_times = []
        ex_cycle_execution_times = []
  
        unit_manager = radical.pilot.UnitManager(session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(pilot_object)

        for i in range(self.nr_cycles):

            start = datetime.datetime.utcnow()
            # returns compute objects
            #print "md unit manager id: %s" % md_unit_manager.uid
            compute_replicas = md_kernel.prepare_replicas_for_md(replicas, self.resource)
            submitted_replicas = unit_manager.submit_units(compute_replicas)
            unit_manager.wait_units()
            ####################################
            # 
            units = unit_manager.get_units()
            temp_sub = []
            temp_stop = []
            for unit in units:
                if unit.uid not in processed_unit_ids:
                    temp_sub.append( (unit.submission_time - datetime.datetime(1970,1,1)).total_seconds() )
                    temp_stop.append( (unit.stop_time - datetime.datetime(1970,1,1)).total_seconds() )
                    processed_unit_ids.append( unit.uid )
            print "for md temp_sub was:"
            print temp_sub
            md_cycle_execution_times.append( max(temp_stop) - min(temp_sub) )
            

            # this is not done for the last cycle
            if (i != (self.nr_cycles-1)):
                #####################################################################
                # computing swap matrix
                #####################################################################
                exchange_replicas = md_kernel.prepare_replicas_for_exchange(replicas)
                submitted_replicas = unit_manager.submit_units(exchange_replicas)
                unit_manager.wait_units()

                ####################################
                # 
                temp_sub = []
                temp_stop = []
                units = unit_manager.get_units()
                for unit in units:
                    if unit.uid not in processed_unit_ids:
                        temp_sub.append( (unit.submission_time - datetime.datetime(1970,1,1)).total_seconds() )
                        temp_stop.append( (unit.stop_time - datetime.datetime(1970,1,1)).total_seconds() )
                        processed_unit_ids.append( unit.uid )

                print "for ex temp_sub was:"
                print temp_sub
                ex_cycle_execution_times.append( max(temp_stop) - min(temp_sub) )

                #####################################################################
                # compose swap matrix from individual files
                #####################################################################
                swap_matrix = self.compose_swap_matrix(replicas)
            
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

            stop = datetime.datetime.utcnow()
            total_cycle_times.append( (stop - start).total_seconds() )

        #######################################################################
        print "md cycle execution times: "
        print md_cycle_execution_times

        print "ex cycle execution times: "
        print ex_cycle_execution_times

        print "total cycle execution times: "
        print total_cycle_times
        ##############################################

        #all_units = []
        #all_sub_times = []
        #all_start_times = []
        #all_stop_times = []

        #all_units = md_units + ex_units
        #for unit in all_units:
        #    all_sub_times.append( (unit.submission_time - datetime.datetime(1970,1,1)).total_seconds() )
        #    all_start_times.append( (unit.start_time - datetime.datetime(1970,1,1)).total_seconds() )
        #    all_stop_times.append( (unit.stop_time - datetime.datetime(1970,1,1)).total_seconds() )

        #pilot_runtime = max(all_stop_times) - min(all_sub_times)
        #print "pilot runtime was: %f" % pilot_runtime

