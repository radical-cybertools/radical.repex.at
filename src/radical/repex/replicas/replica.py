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

#-------------------------------------------------------------------------------

class Replica1d(object):
    """Class representing replica and it's associated data.
    """
    def __init__(self, my_id, new_temperature=None, new_salt_concentration=None, new_restraints=None, rstr_val_1=None,  coor=None, indx1=None, indx2=None, cores=1):
        """Constructor.

        Arguments:
        my_id - integer representing replica's id
        new_temperature - temperature at which replica is initialized (default: None)
        cores - number of cores to be used by replica's NAMD instance (default: 1)
        """
        self.id = int(my_id)
        self.sid = int(my_id)
        self.state = 'I'
        self.cycle = 0

        if rstr_val_1 is None:
            self.rstr_val_1 = 0
        else:
            self.rstr_val_1 = rstr_val_1

        if coor is not None:
            self.coor_file = coor

        if indx1 is not None:
            self.indx1 = indx1

        if indx2 is not None:
            self.indx2 = indx2

        #---------------------------------------------------------
        if new_temperature is None:
            self.new_temperature = 0
        else:
            self.new_temperature = new_temperature
        self.old_temperature = new_temperature
        
        #---------------------------------------------------------
        if new_salt_concentration is None:
            self.new_salt_concentration = 0
        else:
            self.new_salt_concentration = new_salt_concentration
        self.old_salt_concentration = new_salt_concentration
        #---------------------------------------------------------

        if new_restraints is None:
            self.new_restraints = ''
        else:
            self.new_restraints = new_restraints
        self.old_restraints = new_restraints
        #---------------------------------------------------------

        self.potential = 0

        # amber stuff
        self.new_traj = ""
        self.new_info = ""
        self.old_traj = ""
        self.old_info = ""
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
        self.stopped_run = -1

#-------------------------------------------------------------------------------

class Replica2d(object):
    """Class representing replica and it's associated data.
    """
    def __init__(self, my_id, new_temperature=None, new_salt_concentration=None, cores=1):
        """Constructor.

        """
        self.id = int(my_id)
        self.sid = int(my_id)
        self.cycle = 0
        if new_salt_concentration is None:
            self.new_salt_concentration = 0
        else:
            self.new_salt_concentration = new_salt_concentration
        self.old_salt_concentration = new_salt_concentration

        if new_temperature is None:
            self.new_temperature = 0
        else:
            self.new_temperature = new_temperature
        self.old_temperature = new_temperature

        self.potential = 0

        # amber stuff
        self.new_traj = ""  # ok
        self.new_info = ""  # ok
        self.new_coor = ""  # ok both namd and amber


        self.old_traj = ""  # ok
        self.old_info = ""  # ok 
        self.old_coor = ""  # ok both namd and amber
        ###################

        
        self.new_vel = ""         # namd only
        self.new_history = ""     # namd only
        self.new_ext_system = ""  # namd only
        self.old_vel = ""         # namd only
        self.old_ext_system = ""  # namd only


        self.old_path = ""
        self.first_path = ""
        self.swap = 0
        self.cores = cores
        self.stopped_run = -1

#-------------------------------------------------------------------------------

class Replica3d(object):
    """Class representing replica and it's associated data.
       US = Umbrella Sampling
    """
    def __init__(self, my_id, new_temperature=None, new_salt=None, new_restraints=None, rstr_val_1=None, rstr_val_2=None, coor=None, indx1=None, indx2=None, cores=1):
        """Constructor.

        Arguments:
        my_id - integer representing replica's id
        new_temperature - temperature at which replica is initialized (default: None)
        cores - number of cores to be used by replica's NAMD instance (default: 1)
        """
        self.id = int(my_id)
        self.sid = int(my_id)
        self.state = 'I'
        self.cycle = 0

        if coor is not None:
            self.coor_file = coor

        if indx1 is not None:
            self.indx1 = indx1

        if indx2 is not None:
            self.indx2 = indx2

        if new_salt is None:
            self.new_salt_concentration = 0
        else:
            self.new_salt_concentration = new_salt
        self.old_salt_concentration = new_salt

        if new_restraints is None:
            self.new_restraints = ''
            self.old_restraints = ''
        else:
            self.new_restraints = new_restraints
            self.old_restraints = new_restraints
        self.potential_1 = 0

        if new_temperature is None:
            self.new_temperature = 0
        else:
            self.new_temperature = new_temperature
        self.old_temperature = new_temperature

        if rstr_val_1 is None:
            self.rstr_val_1 = 0
        else:
            self.rstr_val_1 = rstr_val_1

        if rstr_val_2 is None:
            self.rstr_val_2 = 0
        else:
            self.rstr_val_2 = rstr_val_2

        # amber stuff
        self.new_traj = ""  # ok
        self.new_info = ""  # ok
        self.new_coor = ""  # ok both namd and amber


        self.old_traj = ""  # ok
        self.old_info = ""  # ok 
        self.old_coor = ""  # ok both namd and amber
        ###################
        ###################

        self.old_path = ""
        self.first_path = ""
        self.swap = 0
        self.cores = cores
        self.stopped_run = -1