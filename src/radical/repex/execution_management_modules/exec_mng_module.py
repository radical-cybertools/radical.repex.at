"""
.. module:: radical.repex.execution_management_modules.exec_mng_module
.. moduleauthor::  <antons.treikalis@gmail.com>
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
import radical.pilot as rp
import radical.utils as ru
from random import randint
from kernels.kernels import KERNELS

#-------------------------------------------------------------------------------

class ExecutionManagementModule(object):
    """Parent class for all Execution Management Modules. Fro standard REMD 
    simulation typically is needed a single instance of EMM.

    Attributes:
        Way too many
    """

    def __init__(self, inp_file, rconfig, md_logger):
        """
        Args:
            inp_file - simulation input file with parameters specified by user 

            rconfig - resource configuration file
            
            md_logger - logger of associated AMM
        """

        self.logger = md_logger

        # RP's pilot's parameters
        self.resource = rconfig.get('resource')
        self.sandbox = rconfig.get('sandbox')
        self.user = rconfig.get('username')
        self.password = rconfig.get('password')
        self.project = rconfig.get('project')
        self.queue = rconfig.get('queue')
        self.cores = int(rconfig.get('cores'))
        self.runtime = int(rconfig.get('runtime'))
        self.dburl = rconfig.get('mongo_url')
        self.access_schema = rconfig.get('access_schema')

        self.cycletime = float(rconfig.get('cycletime', 10.0))

        # check if was set in rconfig
        if self.dburl is None:
            # check if was set as environment variable
            # self.dburl = os.environ.get('RADICAL_PILOT_DBURL')
            # use default dburl
            if self.dburl is None:
                self.logger.info("Using default Mongo DB url")
                self.dburl = "mongodb://144.76.72.175:27017/repex-runs"

        cleanup = rconfig.get('cleanup','False')
        if (cleanup == "True"):
            self.cleanup = True
        else:
            self.cleanup = False 

        self.session = None
        self.pilot_manager = None
        self.pilot_object = None

    #---------------------------------------------------------------------------
    #
    def launch_pilot(self):
        """This method is used to submit RP's pilot to a targer HPC resource.
        Note: by default we wait for a pilot to become active on resource, so
        this method is blocking
        """
 
        #-----------------------------------------------------------------------
        #
        def pilot_state_cb(pilot, state):
            if pilot:
                self.logger.info("ComputePilot '{0}' state changed to {1}.".format(pilot.uid, state) )

                if state == rp.states.FAILED:
                    self.logger.error("Pilot error: {0}".format(pilot.log) )
                    self.logger.error("RepEx execution FAILED.")
                    sys.exit(1)
        #-----------------------------------------------------------------------

        self._prof = ru.Profiler(self.name)
        self._prof.prof('launch_pilot_start')
   
        self.session = rp.Session(database_url=self.dburl)
        self.logger.info("Session ID: {0}".format(self.session.uid) )

        try:
            self._prof.prof('prepare_pd_start')
            if self.user:
                cred = rp.Context('ssh')
                cred.user_id = self.user
                self.session.add_context(cred)

            self.pilot_manager = rp.PilotManager(session=self.session)
            self.pilot_manager.register_callback(pilot_state_cb)

            pilot_description = rp.ComputePilotDescription()
            if self.access_schema == "gsissh":
                pilot_description.access_schema = "gsissh"

            if self.resource.startswith("localhost"):
                pilot_description.resource = "local.localhost"

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

            self._prof.prof('prepare_pd_end')
            self._prof.prof('submit_pilots_start')
            self.pilot_object = self.pilot_manager.submit_pilots(pilot_description)
            self._prof.prof('submit_pilots_end')

            self.logger.info("Pilot ID: {0}".format(self.pilot_object.uid) )

            self._prof.prof('wait_pilots_start')
            self.pilot_manager.wait_pilots(self.pilot_object.uid,'Active') 
            self._prof.prof('wait_pilots_start')

        except rp.PilotException, ex:
            self.logger.error("Error: {0}".format(ex))
            self.session.close (cleanup=True, terminate=True) 

        self._prof.prof('launch_pilot_end')

