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
import time
from os import path
import radical.pilot
from kernels.kernels import KERNELS
import radical.utils.logger as rul

#-----------------------------------------------------------------------------------------------------------------------------------

class PilotKernel(object):
    """
    """
    def __init__(self, inp_file):
        """Constructor.

        Arguments:
        inp_file - json input file with Pilot and NAMD related parameters as specified by user 
        """

        self.name = 'pk'
        self.logger  = rul.getLogger ('radical.repex', self.name)
        
        # pilot parameters
        self.resource = inp_file['input.PILOT']['resource']
        try:
            self.sandbox = inp_file['input.PILOT']['sandbox']
        except:
            self.sandbox = None
      
        self.user = inp_file['input.PILOT']['username']
        try:
            self.password = inp_file['input.PILOT']['password']
        except:
            self.password = None
        try:
            self.project = inp_file['input.PILOT']['project']
        except:
            self.project = None

        try:
            self.queue = inp_file['input.PILOT']['queue']
        except:
            self.queue = None
        try:
            self.cores = int(inp_file['input.PILOT']['cores'])
        except:
            self.logger.info("Field 'cores' must be defined" )
            
        self.runtime = int(inp_file['input.PILOT']['runtime'])
        try:
            self.dburl = inp_file['input.PILOT']['mongo_url']
        except:
            self.logger.info("Using default Mongo DB url" )
            self.dburl = "mongodb://ec2-54-221-194-147.compute-1.amazonaws.com:24242/"
        cleanup = inp_file['input.PILOT']['cleanup']
        if (cleanup == "True"):
            self.cleanup = True
        else:
            self.cleanup = False 


    # --------------------------------------------------------------------------
    #
    def launch_pilot(self):
        """Launches a Pilot on a target resource. This function uses parameters specified in <input_file>.json 

        Returns:
        session - radical.pilot.Session object, the *root* object for all other RADICAL-Pilot objects
        pilot_object - radical.pilot.ComputePilot object
        pilot_manager - radical.pilot.PilotManager object
        """
 
        # --------------------------------------------------------------------------
        #
        def pilot_state_cb(pilot, state):
            """This is a callback function. It gets called very time a ComputePilot changes its state.
            """
           
            if pilot:
                self.logger.info("ComputePilot '{0}' state changed to {1}.".format(pilot.uid, state) )

                if state == radical.pilot.states.FAILED:
                    self.logger.error("Pilot error: {0}".format(pilot.log) )
                    self.logger.error("RepEx execution FAILED.")
                    # sys.exit(1)
        # --------------------------------------------------------------------------

        session = None
        pilot_manager = None
        pilot_object = None
   
        session = radical.pilot.Session(database_url=self.dburl, database_name='radicalpilot')
        self.logger.info("Session ID: {0}".format(session.uid) )

        try:
            # Add an ssh identity to the session.
            cred = radical.pilot.Context('ssh')
            cred.user_id = self.user
            session.add_context(cred)

            pilot_manager = radical.pilot.PilotManager(session=session)
            pilot_manager.register_callback(pilot_state_cb)

            pilot_description = radical.pilot.ComputePilotDescription()
            if self.resource.startswith("localhost"):
                pilot_description.resource = "local.localhost"
            else:
                pilot_description.resource = self.resource

            if(self.sandbox != None):
                pilot_description.sandbox = str(self.sandbox)

            if(self.project != None):
                pilot_description.project = str(self.project)   

            if(self.queue != None):
                pilot_description.queue = str(self.queue)

            pilot_description.cores = self.cores
            pilot_description.runtime = self.runtime
            pilot_description.cleanup = self.cleanup

            pilot_object = pilot_manager.submit_pilots(pilot_description)

            # we wait for the pilot to start running on resource
            self.logger.info("Pilot ID: {0}".format(pilot_object.uid) )
            pilot_manager.wait_pilots(pilot_object.uid,'Active') 
            

        except radical.pilot.PilotException, ex:
            self.logger.error("Error: {0}".format(ex))

        return pilot_manager, pilot_object, session

