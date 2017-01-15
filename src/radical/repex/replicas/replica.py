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

class Replica(object):
    
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
                 nr_dims = 1):
    
        self.id = int(my_id)
        self.sid = int(my_id)
        self.state = 'I'
        self.cycle = 0
        self.sim_cycle = 0
        self.group_idx = [None, None, None]
        self.cur_dim = 1

        if coor is not None:
            self.coor_file = coor

        if new_restraints is None:
            self.new_restraints = ''
        else:
            self.new_restraints = new_restraints

        self.dims = {}

        if nr_dims == 1:
            self.dims['d1'] = {'par' : d1_param, 'old_par' : d1_param, 'type' : d1_type} 
        elif nr_dims == 2:
            self.dims['d1'] = {'par' : d1_param, 'old_par' : d1_param, 'type' : d1_type} 
            self.dims['d2'] = {'par' : d2_param, 'old_par' : d2_param, 'type' : d2_type} 
        elif nr_dims == 3:
            self.dims['d1'] = {'par' : d1_param, 'old_par' : d1_param, 'type' : d1_type} 
            self.dims['d2'] = {'par' : d2_param, 'old_par' : d2_param, 'type' : d2_type} 
            self.dims['d3'] = {'par' : d3_param, 'old_par' : d3_param, 'type' : d3_type}

        self.new_traj = ""  # ok
        self.new_info = ""  # ok
        self.new_coor = ""  # ok both namd and amber

        self.old_traj = ""  # ok
        self.old_info = ""  # ok 
        self.old_coor = ""  # ok both namd and amber

        self.old_path = ""
        self.first_path = ""
        self.swap = 0

