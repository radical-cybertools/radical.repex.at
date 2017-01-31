"""
.. module:: radical.repex.replica_cleanup
.. moduleauthor::  <antons.treikalis@gmail.com>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import shutil

#-------------------------------------------------------------------------------

class Restart(object):
    """Maintains the state of the simulation, which is saved to .pkl files after 
    every simulation cycle. 

    Attributes:
        new_sandbox - path to RP sandbox on remote HPC cluster for current 
        simulation 

        old_sandbox - path to RP sandbox on remote HPC cluster for simulation 
        we are restarting

        dimension - index of the current dimension of simulation

        current_cycle - index of the current cycle of simulation

        groups_numbers - list of the number of groups in each dimension
    """
    def __init__(self, dimension=None, current_cycle=None, new_sandbox=None):
        self.new_sandbox    = new_sandbox
        self.old_sandbox    = None
        self.dimension      = dimension
        self.current_cycle  = current_cycle
        self.groups_numbers = None

 