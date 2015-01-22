"""
.. module:: radical.repex.pilot_kernels.pilot_kernel_pattern_b
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
import radical.utils.logger as rul

#-----------------------------------------------------------------------------------------------------------------------------------

class PilotKernelPatternB2d(PilotKernel):
    """This class is responsible for performing all Radical Pilot related operations for RE pattern B.
    This includes pilot launching, running main loop of RE simulation and using RP API for data staging in and out. 

    RE pattern B:
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
        inp_file - json input file with Pilot and NAMD related parameters as specified by user 
        """
        PilotKernel.__init__(self, inp_file)

        self.name = 'pk-patternB-2d'
        self.logger  = rul.getLogger ('radical.repex', self.name)

#-----------------------------------------------------------------------------------------------------------------------------------
    def getkey(self, item):
        return item[0]


    def compose_swap_matrix(self, replicas, matrix_columns):
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

#-----------------------------------------------------------------------------------------------------------------------------------

    def run_simulation(self, replicas, pilot_object, session,  md_kernel ):
        """This function runs the main loop of RE simulation for RE pattern B.

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
            self.get_logger().info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )

            if state == radical.pilot.states.FAILED:
                self.get_logger().error("Log: {0:s}".format( unit.log[-1] ) )  


        unit_manager = radical.pilot.UnitManager(session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(pilot_object)

        # staging shared input data in
        shared_data_unit_descr = md_kernel.prepare_shared_md_input()
        staging_unit = unit_manager.submit_units(shared_data_unit_descr)
        unit_manager.wait_units()

        # get the path to the directory containing the shared data
        shared_data_url = radical.pilot.Url(staging_unit.working_directory).path

        for r in replicas:
            self.get_logger().info("Replica: id={0} salt={1} temperature={2}".format(r.id, r.new_salt_concentration, r.new_temperature) )

        md_kernel.init_matrices(replicas)

        for i in range(md_kernel.nr_cycles):

            current_cycle = i+1
            start_time = datetime.datetime.utcnow()
           
            self.get_logger().info("Performing cycle: {0}".format(current_cycle) )
            #########
            # D1 run (temperature exchange)
            D = 1
            self.get_logger().info("Dim 1: preparing {0} replicas for MD run; cycle {1}".format(md_kernel.replicas, current_cycle) )
            compute_replicas = md_kernel.prepare_replicas_for_md(replicas, shared_data_url)
            self.get_logger().info("Dim 1: submitting {0} replicas for MD run; cycle {1}".format(md_kernel.replicas, current_cycle) )
            submitted_replicas = unit_manager.submit_units(compute_replicas)
            unit_manager.wait_units()
            
            stop_time = datetime.datetime.utcnow()
            self.get_logger().info("Dim 1: cycle {0}; time to perform MD run: {1:0.3f}".format(current_cycle, (stop_time-start_time).total_seconds())) 
            # this is not done for the last cycle
            if (i != (md_kernel.nr_cycles-1)):
                start_time = datetime.datetime.utcnow()
                #########################################
                # computing swap matrix
                #########################################
                self.get_logger().info("Dim 1: preparing {0} replicas for Exchange run; cycle {1}".format(md_kernel.replicas, current_cycle) )
                #########################################
                # selecting replicas for exchange step
                #########################################

                exchange_replicas = md_kernel.prepare_replicas_for_exchange(D, replicas, shared_data_url)
                self.get_logger().info("Dim 1: submitting {0} replicas for Exchange run; cycle {1}".format(md_kernel.replicas, current_cycle) )
                submitted_replicas = unit_manager.submit_units(exchange_replicas)
                unit_manager.wait_units()
                stop_time = datetime.datetime.utcnow()
                self.get_logger().info("Dim 1: cycle {0}; time to perform Exchange: {1:0.3f}".format(current_cycle, (stop_time-start_time).total_seconds()))
                start_time = datetime.datetime.utcnow()

                matrix_columns = []
                for r in submitted_replicas:
                    d = str(r.stdout)
                    data = d.split()
                    matrix_columns.append(data)

                ##############################################
                # compose swap matrix from individual files
                ##############################################
                self.get_logger().info("Dim 1: composing swap matrix from individual files for all replicas")
                swap_matrix = self.compose_swap_matrix(replicas, matrix_columns)
            
                self.get_logger().info("Dim 1: performing exchange")
                md_kernel.select_for_exchange(D, replicas, swap_matrix, current_cycle)

                stop_time = datetime.datetime.utcnow()
                self.get_logger().info("Dim 1: cycle {0}; post-processing time: {1:0.3f}".format(current_cycle, (stop_time-start_time).total_seconds()))
 
            start_time = datetime.datetime.utcnow()
            #########################################
            # D2 run (salt concentration exchange)
            D = 2
            self.get_logger().info("Dim 2: preparing {0} replicas for MD run; cycle {1}".format(md_kernel.replicas, current_cycle) )
            compute_replicas = md_kernel.prepare_replicas_for_md(replicas, shared_data_url)
            self.get_logger().info("Dim 2: submitting {0} replicas for MD run; cycle {1}".format(md_kernel.replicas, current_cycle) )
            submitted_replicas = unit_manager.submit_units(compute_replicas)
            unit_manager.wait_units()

            stop_time = datetime.datetime.utcnow()
            self.get_logger().info("Dim 2: cycle %d; time to perform MD run: {1:0.3f}".format(current_cycle, (stop_time-start_time).total_seconds()))

            
            # this is not done for the last cycle
            if (i != (md_kernel.nr_cycles-1)):
                start_time = datetime.datetime.utcnow()
                ##########################
                # computing swap matrix
                ##########################
                self.get_logger().info("Dim 2: preparing {0} replicas for Exchange run; cycle {1}".format(md_kernel.replicas, current_cycle) )
                exchange_replicas = md_kernel.prepare_replicas_for_exchange(D, replicas, shared_data_url)
                self.get_logger().info("Dim 2: submitting {0} replicas for Exchange run; cycle {1}".format(md_kernel.replicas, current_cycle) )
                submitted_replicas = unit_manager.submit_units(exchange_replicas)
                unit_manager.wait_units()
          
                stop_time = datetime.datetime.utcnow()
                self.get_logger().info("Dim 2: cycle {0}; time to perform Exchange: {1:0.3f}".format(current_cycle, (stop_time-start_time).total_seconds()))
                start_time = datetime.datetime.utcnow()

                matrix_columns = []
                for r in submitted_replicas:
                    d = str(r.stdout)
                    data = d.split()
                    matrix_columns.append(data)

                ##############################################
                # compose swap matrix from individual files
                ##############################################
                self.get_logger().info("Dim 2: Composing swap matrix from individual files for all replicas")
                swap_matrix = self.compose_swap_matrix(replicas, matrix_columns)
            
                self.get_logger().info("Dim 2: Performing exchange of salt concentrations")
                md_kernel.select_for_exchange(D, replicas, swap_matrix, current_cycle)

                stop_time = datetime.datetime.utcnow()
                self.get_logger().info("Dim 2: cycle {0}; post-processing time: {1:0.3f}".format(current_cycle, (stop_time-start_time).total_seconds()))

        # end of loop
        d1_id_matrix = md_kernel.get_d1_id_matrix()
        temp_matrix = md_kernel.get_temp_matrix()
        
        d2_id_matrix = md_kernel.get_d2_id_matrix()
        salt_matrix = md_kernel.get_salt_matrix()

        self.get_logger().debug("Exchange matrix of replica id's for Dim 1 (temperature) exchange: {0:s}".format(d1_id_matrix) )
         
        self.get_logger().debug("Change in temperatures for each replica: : {0:s}".format(temp_matrix) )
       
        self.get_logger().debug("Exchange matrix of replica id's for Dim 2 (salt concentration) exchange: {0:s}".format(d2_id_matrix) )

        self.get_logger().debug("Change in salt concentration for each replica: {0:s}".format(salt_matrix) )
        
