"""
.. module:: radical.repex.replicas.replica
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import math
import json

#-----------------------------------------------------------------------------------------------------------------------------------

class Replica(object):
    """Class representing replica and it's associated data.
    """
    def __init__(self, my_id, new_temperature=None, cores=1):
        """Constructor.

        Arguments:
        my_id - integer representing replica's id
        new_temperature - temperature at which replica is initialized (default: None)
        cores - number of cores to be used by replica's NAMD instance (default: 1)
        """
        self.id = my_id
        self.sid = my_id
        self.state = 'I'
        self.cycle = 0
        if new_temperature is None:
            self.new_temperature = 0
        else:
            self.new_temperature = new_temperature
        self.old_temperature = new_temperature
        self.potential = 0

        # amber stuff
        self.new_traj = ""
        self.new_info = ""
        self.old_traj = ""
        ###################

        self.new_coor = ""
        self.new_vel = ""
        self.new_history = ""
        self.new_ext_system = "" 
        self.old_coor = ""
        self.old_vel = ""
        self.old_ext_system = "" 
        self.old_path = ""
        self.first_path = ""
        self.swap = 0
        self.cores = cores

