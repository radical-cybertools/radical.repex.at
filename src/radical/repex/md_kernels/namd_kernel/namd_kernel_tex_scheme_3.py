"""
.. module:: radical.repex.namd_kernels.namd_kernel_scheme_3
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
from os import path
from namd_kernel_tex import *

#-----------------------------------------------------------------------------------------------------------------------------------

class NamdKernelTexScheme3(NamdKernelTex):
    """This class is responsible for performing all operations related to NAMD for RE scheme 3.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.

    RE scheme 3:
    - Asynchronous RE scheme: MD run on target resource is overlapped with local exchange step. Thus both MD run
    and exchange step are asynchronous.  
    - Number of replicas is greater than number of allocated resources.
    - Replica simulation cycle is defined by the fixed number of simulation time-steps each replica has to perform.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed locally
    Overall algorithm is as follows:
        - First replicas in "waiting" state are submitted to pilot.
        - Then fixed time interval (cycle_time in input.json) must elapse before exchange step may take place.
        - After this fixed time interval elapsed, some replicas are still running on target resource.
        - In local exchange step are participating replicas which had finished MD run (state "finished") and
        replicas in "waiting" state.
        - After local exchanges step is performed replicas which participated in exchange are submitted to pilot
        to perform next simulation cycle
    """
    def __init__(self, inp_file,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        NamdKernelTex.__init__(self, inp_file, work_dir_local)

#-----------------------------------------------------------------------------------------------------------------------------------

    def check_replicas(self, replicas):
        """
        """
        finished_replicas = []
        files = os.listdir( self.work_dir_local )

        for r in replicas:
            history_name =  self.inp_basename[:-5] + "_%s_%s.history" % ( r.id, (r.cycle-1) )
            for item in files:
                if (item.startswith(history_name)):
                    if r not in finished_replicas:
                        finished_replicas.append( r )

        return finished_replicas

