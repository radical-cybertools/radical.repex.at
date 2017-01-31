"""
.. module:: radical.repex.replicas.replica
.. moduleauthor::  <antons.treikalis@gmail.com>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import math
import json

#-------------------------------------------------------------------------------

class Replica(object):
    """Class representing a replica object. Should be used for both Amber 
    and NAMD.

    Attributes:
        id - ID of this replica

        sid - state id of this replica

        state - letter, representing state of this replica. Mainly used for 
        asynchronous RE. possible states are:
            I  - initiaized
            MD - replica is performing MD simulation
            EX - replica is performing Exchange

        group_idx - list with group indexes of this replica in each dimension

        dims - dictionary holding parameters and types of each dimension
    """

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
        """
        Args:
            my_id - replica id

            d1_param - parameter in first dimension
            
            d2_param - parameter in second dimension

            d3_param - parameter in third dimension

            d1_type - type of exchange in first dimension

            d2_type - type of exchange in second dimension

            d3_type - type of exchange in third dimension

            new_restraints - name of restraint file template

            coor - name of coordinates file

            nr_dims - number of dimenions for this replica
        """
    
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

        self.new_traj = ""
        self.new_info = ""
        self.new_coor = ""  # namd and amber

        self.old_traj = ""
        self.old_info = ""
        self.old_coor = ""  # namd and amber

        self.old_path   = ""
        self.first_path = ""
        self.swap       = 0

