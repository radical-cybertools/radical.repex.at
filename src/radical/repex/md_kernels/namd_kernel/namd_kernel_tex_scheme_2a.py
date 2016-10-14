"""
.. module:: radical.repex.namd_kernels.namd_kernel_scheme_2a
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

from namd_kernel_tex import *

#-----------------------------------------------------------------------------------------------------------------------------------

class NamdKernelTexScheme2a(NamdKernelTex):
    """This class is responsible for performing all operations related to NAMD for RE scheme 2a.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.

    RE scheme 2a:
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

        NamdKernelTex.__init__(self, inp_file, work_dir_local)

