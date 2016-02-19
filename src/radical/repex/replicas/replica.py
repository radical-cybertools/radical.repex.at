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

    def __init__(self, my_id,  
                 d1_param=0.0, 
                 d1_type = None, 
                 new_restraints=None, 
                 coor=None, 
                 cores=1):
       
        self.id = int(my_id)
        self.sid = int(my_id)
        self.state = 'I'
        self.cycle = 0

        if coor is not None:
            self.coor_file = coor

        if new_restraints is None:
            self.new_restraints = ''
            self.old_restraints = ''
        else:
            self.new_restraints = new_restraints
            self.old_restraints = new_restraints

        self.dims = {}
        self.dims['d1'] = {'par' : d1_param, 'old_par' : d1_param, 'type' : d1_type} 

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
    
    def __init__(self, 
                 my_id,  
                 d1_param=0.0, 
                 d2_param=0.0, 
                 d1_type = None, 
                 d2_type = None, 
                 new_restraints=None, 
                 coor=None, 
                 cores=1):
        
        self.id = int(my_id)
        self.sid = int(my_id)
        self.cycle = 0

        self.group_idx = [None, None]

        if coor is not None:
            self.coor_file = coor

        if new_restraints is None:
            self.new_restraints = ''
            self.old_restraints = ''
        else:
            self.new_restraints = new_restraints
            self.old_restraints = new_restraints

        self.dims = {}
        self.dims['d1'] = {'par' : d1_param, 'old_par' : d1_param, 'type' : d1_type} 
        self.dims['d2'] = {'par' : d2_param, 'old_par' : d2_param, 'type' : d2_type} 

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

#-------------------------------------------------------------------------------

class Replica3d(object):
    
    def __init__(self, 
                 my_id, 
                 d1_param=0.0, 
                 d2_param=0.0, 
                 d3_param=0.0, 
                 d1_type = None, 
                 d2_type = None, 
                 d3_type = None, 
                 new_restraints=None, 
                 coor=None, 
                 cores=1):
    
        self.id = int(my_id)
        self.sid = int(my_id)
        self.state = 'I'
        self.cycle = 0
        self.group_idx = [None, None, None]

        if coor is not None:
            self.coor_file = coor

        if new_restraints is None:
            self.new_restraints = ''
            self.old_restraints = ''
        else:
            self.new_restraints = new_restraints
            self.old_restraints = new_restraints

        self.dims = {}
        self.dims['d1'] = {'par' : d1_param, 'old_par' : d1_param, 'type' : d1_type} 
        self.dims['d2'] = {'par' : d2_param, 'old_par' : d2_param, 'type' : d2_type} 
        self.dims['d3'] = {'par' : d3_param, 'old_par' : d3_param, 'type' : d3_type} 

        # amber stuff
        self.new_traj = ""  # ok
        self.new_info = ""  # ok
        self.new_coor = ""  # ok both namd and amber

        self.old_traj = ""  # ok
        self.old_info = ""  # ok 
        self.old_coor = ""  # ok both namd and amber

        self.old_path = ""
        self.first_path = ""
        self.swap = 0
        self.cores = cores

