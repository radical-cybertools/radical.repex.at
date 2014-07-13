"""
.. module:: radical.repex.md_kernels.amber_kernels_tex.amber_kernel_tex_scheme_3
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
from os import path
from amber_kernel_tex import *

#-----------------------------------------------------------------------------------------------------------------------------------

class AmberKernelTexScheme3(AmberKernelTex):
    """This class is responsible for performing all operations related to Amber for RE scheme S2.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.

    RE scheme S2:
    - Synchronous RE scheme: none of the replicas can start exchange before all replicas has finished MD run.
    Conversely, none of the replicas can start MD run before all replicas has finished exchange step. 
    In other words global barrier is present.   
    - Number of replicas is greater than number of allocated resources for both MD and exchange step.
    - Simulation cycle is defined by the fixed number of simulation time-steps for each replica.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed in decentralized fashion on target resource.

    """
    def __init__(self, inp_file,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        AmberKernelTex.__init__(self, inp_file, work_dir_local)

#-----------------------------------------------------------------------------------------------------------------------------------

    def check_replicas(self, replicas):
        """
        """
        finished_replicas = []
        files = os.listdir( self.work_dir_local )

        for r in replicas:

            history_name =  r.new_history
            for item in files:
                if (item.startswith(history_name)):
                    if r not in finished_replicas:
                        finished_replicas.append( r )

        return finished_replicas

