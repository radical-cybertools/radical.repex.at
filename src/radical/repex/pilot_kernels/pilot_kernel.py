"""
.. module:: radical.repex.pilot_kernels.pilot_kernel
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import math
import json
from os import path
import radical.pilot
from kernels.kernels import KERNELS

#-----------------------------------------------------------------------------------------------------------------------------------

class PilotKernel(object):
    """
    """
    def __init__(self, inp_file):
        """Constructor.

        Arguments:
        inp_file - json input file with Pilot and NAMD related parameters as specified by user 
        """
        
        # pilot parameters
        self.resource = inp_file['input.PILOT']['resource']
        try:
            self.sandbox = inp_file['input.PILOT']['sandbox']
        except:
            self.sandbox = None
      
        self.user = inp_file['input.PILOT']['username']
        try:
            self.project = inp_file['input.PILOT']['project']
        except:
            self.project = None

        try:
            self.cores = int(inp_file['input.PILOT']['cores'])
        except:
            try:
                nr_replicas = int(inp_file['input.MD']['number_of_replicas'])
            except:
                print "Field 'number_of_replicas' must be defined!"

            #node_size = KERNELS[self.resource]["params"]["cores"]
            self.cores = nr_replicas / 2
            print "Using default core count equal %s" %  self.cores
        self.runtime = int(inp_file['input.PILOT']['runtime'])
        try:
            self.dburl = inp_file['input.PILOT']['mongo_url']
        except:
            print "Using default Mongo DB url"
            self.dburl = "mongodb://ec2-184-72-89-141.compute-1.amazonaws.com:27017/"
        cleanup = inp_file['input.PILOT']['cleanup']
        if (cleanup == "True"):
            self.cleanup = True
        else:
            self.cleanup = False 

#-----------------------------------------------------------------------------------------------------------------------------------

    def launch_pilot(self):
        """Launches a Pilot on a target resource. This function uses parameters specified in <input_file>.json 

        Returns:
        session - radical.pilot.Session object, the *root* object for all other RADICAL-Pilot objects
        pilot_object - radical.pilot.ComputePilot object
        pilot_manager - radical.pilot.PilotManager object
        """
        session = None
        pilot_manager = None
        pilot_object = None
   
        try:
            session = radical.pilot.Session(database_url=self.dburl)

            # Add an ssh identity to the session.
            cred = radical.pilot.Context('ssh')
            cred.user_id = self.user
            session.add_context(cred)

            pilot_manager = radical.pilot.PilotManager(session=session)
            pilot_manager.register_callback(pilot_state_cb)

            pilot_descripiton = radical.pilot.ComputePilotDescription()
            if self.resource.startswith("localhost"):
                pilot_descripiton.resource = "localhost:local"
            else:
                pilot_descripiton.resource = self.resource

            if(self.sandbox != None):
                pilot_descripiton.sandbox = str(self.sandbox)

            if(self.project != None):
                pilot_descripiton.project = str(self.project)   

            pilot_descripiton.cores = self.cores
            pilot_descripiton.runtime = self.runtime
            pilot_descripiton.cleanup = self.cleanup

            pilot_object = pilot_manager.submit_pilots(pilot_descripiton)

        except radical.pilot.PilotException, ex:
            print "Error: %s" % ex

        return pilot_manager, pilot_object, session

#-----------------------------------------------------------------------------------------------------------------------------------

def unit_state_change_cb(unit, state):
    """This is a callback function. It gets called very time a ComputeUnit changes its state.
    """
    print "[Callback]: ComputeUnit '{0}' state changed to {1}.".format(
        unit.uid, state)
    if state == radical.pilot.states.FAILED:
        print "            Log: %s" % unit.log[-1]

#-----------------------------------------------------------------------------------------------------------------------------------

def pilot_state_cb(pilot, state):
    """This is a callback function. It gets called very time a ComputePilot changes its state.
    """
    print "[Callback]: ComputePilot '{0}' state changed to {1}.".format(
        pilot.uid, state)

    if state == radical.pilot.states.FAILED:
        sys.exit(1)
