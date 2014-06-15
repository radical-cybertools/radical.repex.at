"""
.. module:: radical.repex.pilot_kernels.pilot_kernel_s2
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

#-----------------------------------------------------------------------------------------------------------------------------------

class PilotKernelS2(object):
    """This class is responsible for performing all Radical Pilot related operations for RE scheme S2.
    This includes pilot launching, running main loop of RE simulation and using RP API for data staging in and out. 

    RE scheme S2:
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
        
        # pilot parameters
        self.resource = inp_file['input.PILOT']['resource']
        if self.resource == "localhost.linux.x86":
            self.sandbox = inp_file['input.PILOT']['sandbox']
        else:
            self.sandbox = None
        self.user = inp_file['input.PILOT']['username']
        try:
            self.cores = int(inp_file['input.PILOT']['cores'])
        except:
            self.cores = KERNELS[self.resource]["params"]["cores"]
            print "Using default core count equal %s" %  self.cores
        self.runtime = int(inp_file['input.PILOT']['runtime'])
        try:
            self.dburl = inp_file['input.PILOT']['mongo_url']
        except:
            print "Using default Mongo DB url"
            self.dburl = "mongodb://ec2-184-72-89-141.compute-1.amazonaws.com:27017/"
        self.cleanup = inp_file['input.PILOT']['cleanup']  
        self.nr_cycles = int(inp_file['input.PILOT']['number_of_cycles']) 

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

                # setting old_path for each replica
                r.old_path = lines[1]
            except:
                raise

        return swap_matrix

#-----------------------------------------------------------------------------------------------------------------------------------

    def run_simulation(self, replicas, session, pilot_object, md_kernel ):
        """This function runs the main loop of RE simulation for S2 RE scheme.

        Arguments:
        replicas - list of Replica objects
        session - radical.pilot.session object, the *root* object for all other RADICAL-Pilot objects
        pilot_object - radical.pilot object
        md_kernel - an instance of NamdKernelS2 class
        """
        for i in range(self.nr_cycles):
            # returns compute objects
            compute_replicas = md_kernel.prepare_replicas_for_md(replicas)
            um = radical.pilot.UnitManager(session=session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
            um.register_callback(self.unit_state_change_cb)
            um.add_pilots(pilot_object)

            submitted_replicas = um.submit_units(compute_replicas)
            um.wait_units()

            # this is not done for the last cycle
            if (i != (self.nr_cycles-1)):
                #####################################################################
                # computing swap matrix
                #####################################################################
                exchange_replicas = md_kernel.prepare_replicas_for_exchange(replicas)
                submitted_replicas = um.submit_units(exchange_replicas)
                um.wait_units()
                #####################################################################
                # compose swap matrix from individual files
                #####################################################################
                swap_matrix = self.compose_swap_matrix(replicas)

                print ""
                print "swap matrix was: "
                print swap_matrix
                print ""
            
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
            
#-----------------------------------------------------------------------------------------------------------------------------------

    def launch_pilot(self):
        """Launches a Pilot on a target resource. This function uses parameters specified in config/input.json 

        Returns:
        session - radical.pilot.session object, the *root* object for all other RADICAL-Pilot objects
        pilot_manager - radical.pilot.pilot_manager object
        pilot_object - radical.pilot object
        """
        session = None
        pilot_manager = None
        pilot_object = None
   
        try:
            session = radical.pilot.Session(database_url=self.dburl)

            # Add an ssh identity to the session.
            cred = radical.pilot.SSHCredential()
            cred.user_id = self.user
            session.add_credential(cred)

            pilot_manager = radical.pilot.PilotManager(session=session)
            pilot_manager.register_callback(self.pilot_state_cb)

            pilot_descripiton = radical.pilot.ComputePilotDescription()
            if self.resource.startswith("localhost."):
                pilot_descripiton.sandbox = self.sandbox
                pilot_descripiton.resource = "localhost:local"
            else:
                pilot_descripiton.resource = self.resource
            pilot_descripiton.cores = self.cores
            pilot_descripiton.runtime = self.runtime
            pilot_descripiton.cleanup = self.cleanup

            pilot_object = pilot_manager.submit_pilots(pilot_descripiton)

        except radical.pilot.PilotException, ex:
            print "Error: %s" % ex

        return session, pilot_manager, pilot_object 

#-----------------------------------------------------------------------------------------------------------------------------------

    def unit_state_change_cb(self, unit, state):
        """This is a callback function. It gets called very time a ComputeUnit changes its state.
        """
        print "[Callback]: ComputeUnit '{0}' state changed to {1}.".format(
            unit.uid, state)
        if state == radical.pilot.states.FAILED:
            print "            Log: %s" % unit.log[-1]

#-----------------------------------------------------------------------------------------------------------------------------------

    def pilot_state_cb(self, pilot, state):
        """This is a callback function. It gets called very time a ComputePilot changes its state.
        """
        print "[Callback]: ComputePilot '{0}' state changed to {1}.".format(
            pilot.uid, state)

        if state == radical.pilot.states.FAILED:
            sys.exit(1)

