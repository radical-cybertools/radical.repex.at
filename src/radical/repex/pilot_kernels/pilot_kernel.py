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
import random
import datetime
from os import path
import radical.pilot
from random import randint
from kernels.kernels import KERNELS
import radical.utils.logger as rul

#-------------------------------------------------------------------------------

class PilotKernel(object):
    """
    """
    def __init__(self, inp_file, rconfig):
        """Constructor.

        Arguments:
        inp_file - json input file with Pilot and NAMD related parameters as specified by user 
        """

        self.name = 'exec'
        self.logger  = rul.getLogger ('radical.repex', self.name)
        
        # pilot parameters
        self.resource = rconfig['target'].get('resource')
        self.sandbox = rconfig['target'].get('sandbox')
        self.user = rconfig['target'].get('username')
        self.password = rconfig['target'].get('password')
        self.project = rconfig['target'].get('project')
        self.queue = rconfig['target'].get('queue')
        self.cores = int(rconfig['target'].get('cores'))
            
        self.runtime = int(rconfig['target'].get('runtime'))
        self.dburl = rconfig['target'].get('mongo_url')

        if self.dburl is None:
            self.logger.info("Using default Mongo DB url" )
            self.dburl = "mongodb://ec2-54-221-194-147.compute-1.amazonaws.com:24242/cdi-test"

        cleanup = rconfig['target'].get('cleanup','False')
        if (cleanup == "True"):
            self.cleanup = True
        else:
            self.cleanup = False 

    # --------------------------------------------------------------------------
    #
    def launch_pilot(self):
 
        # ----------------------------------------------------------------------
        #
        def pilot_state_cb(pilot, state):
           
            if pilot:
                self.logger.info("ComputePilot '{0}' state changed to {1}.".format(pilot.uid, state) )

                if state == radical.pilot.states.FAILED:
                    self.logger.error("Pilot error: {0}".format(pilot.log) )
                    self.logger.error("RepEx execution FAILED.")
                    sys.exit(1)
        # ----------------------------------------------------------------------
        
        session = None
        pilot_manager = None
        pilot_object = None
   
        session = radical.pilot.Session(database_url=self.dburl)
        self.logger.info("Session ID: {0}".format(session.uid) )

        try:
            # Add an ssh identity to the session.
            if self.user:
                cred = radical.pilot.Context('ssh')
                cred.user_id = self.user
                session.add_context(cred)

            pilot_manager = radical.pilot.PilotManager(session=session)
            pilot_manager.register_callback(pilot_state_cb)

            pilot_description = radical.pilot.ComputePilotDescription()
            if self.resource == "xsede.stampede.wf":
                pilot_description.access_schema = "gsissh"

            if self.resource.startswith("localhost"):
                pilot_description.resource = "local.localhost"

            if self.resource == "xsede.stampede.wf":
                self.resource = "xsede.stampede"

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
            session.close (cleanup=False) 

        return pilot_manager, pilot_object, session

