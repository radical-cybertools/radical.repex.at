"""
.. module:: radical.repex.md_kernles_tex.amber_kernels_tex.amber_kernel_tex_pattern_b
.. moduleauthor::  <antons.treikalis@rutgers.edu>
.. moduleauthor::  <haoyuan.chen@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import time
import math
import json
import random
import shutil
import datetime
from os import path
import radical.pilot
from kernels.kernels import KERNELS
from replicas.replica import Replica
from amber_kernel_tex import *
import radical.utils.logger as rul
#import amber_kernels_tex.amber_matrix_calculator_scheme_2
import amber_kernels_tex.amber_matrix_calculator_pattern_b

#-----------------------------------------------------------------------------------------------------------------------------------

class AmberKernelTexPatternB(AmberKernelTex):
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

        """
        self.pre_exec = KERNELS[self.resource]["kernels"]["amber"]["pre_execution"]
        try:
            self.amber_path = inp_file['input.MD']['amber_path']
        except:
            print "Using default Amber path for %s" % inp_file['input.PILOT']['resource']
            try:
                self.amber_path = KERNELS[self.resource]["kernels"]["amber"]["executable"]
            except:
                print "Amber path for localhost is not defined..."
        """
 
        self.amber_restraints = inp_file['input.MD']['amber_restraints']
        self.amber_coordinates = inp_file['input.MD']['amber_coordinates']
        self.amber_parameters = inp_file['input.MD']['amber_parameters']
        self.amber_input = inp_file['input.MD']['amber_input']
        self.input_folder = inp_file['input.MD']['input_folder']

        self.name = 'ak-patternB'
        self.logger  = rul.getLogger ('radical.repex', self.name)
 
        self.current_cycle = -1
 
        self.shared_urls = []
        self.shared_files = []

        self.all_temp_list = []
        self.all_salt_list = []

    # ------------------------------------------------------------------------------
    #
    def prepare_shared_data(self):

        parm_path = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_parameters
        rstr_path = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_restraints
        inp_path  = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_input

        calc_b = os.path.dirname(amber_kernels_tex.amber_matrix_calculator_pattern_b.__file__)
        calc_b_path = calc_b + "/amber_matrix_calculator_pattern_b.py"

        self.shared_files.append(self.amber_parameters)
        self.shared_files.append(self.amber_restraints)
        self.shared_files.append(self.amber_input)
        self.shared_files.append("amber_matrix_calculator_pattern_b.py")

        parm_url = 'file://%s' % (parm_path)
        self.shared_urls.append(parm_url)

        rstr_url = 'file://%s' % (rstr_path)
        self.shared_urls.append(rstr_url)

        inp_url = 'file://%s' % (inp_path)
        self.shared_urls.append(inp_url)

        calc_b_url = 'file://%s' % (calc_b_path)
        self.shared_urls.append(calc_b_url)

#-----------------------------------------------------------------------------------------------------------------------------------

    def prepare_replica_for_md(self, replica, sd_shared_list):
        """Prepares all replicas for execution. In this function are created CU descriptions for replicas, are
        specified input/output files to be transferred to/from target system. Note: input files for first and 
        subsequent simulation cycles are different.

        Arguments:
        replicas - list of Replica objects

        Returns:
        compute_replicas - list of radical.pilot.ComputeUnitDescription objects
        """
        
        self.build_input_file(replica)
      
        # rstr = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_restraints
        crds = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_coordinates

        input_file = "%s_%d_%d.mdin" % (self.inp_basename, replica.id, (replica.cycle-1))
        # this is not transferred back
        output_file = "%s_%d_%d.mdout" % (self.inp_basename, replica.id, (replica.cycle-1))

        new_coor = replica.new_coor
        new_traj = replica.new_traj
        new_info = replica.new_info
        old_coor = replica.old_coor
        old_traj = replica.old_traj

        st_out = []
        info_out = {
            'source': new_info,
            'target': 'staging:///%s' % new_info,
            'action': radical.pilot.COPY
        }
        st_out.append(info_out)

        coor_out = {
            'source': new_coor,
            'target': 'staging:///%s' % new_coor,
            'action': radical.pilot.COPY
        }
        st_out.append(coor_out)

        if replica.cycle == 1:       
            replica_path = "replica_%d_%d/" % (replica.id, 0)
            crds_out = {
                'source': self.amber_coordinates,
                'target': 'staging:///%s' % (replica_path + self.amber_coordinates),
                'action': radical.pilot.COPY
            }
            st_out.append(crds_out)
                
            cu = radical.pilot.ComputeUnitDescription()
            cu.executable = self.amber_path
            cu.pre_exec = self.pre_exec
            cu.mpi = self.replica_mpi
            cu.arguments = ["-O", "-i ", input_file, 
                                  "-o ", output_file, 
                                  "-p ", self.amber_parameters, 
                                  "-c ", self.amber_coordinates, 
                                  "-r ", new_coor, 
                                  "-x ", new_traj, 
                                  "-inf ", new_info]

            cu.cores = self.replica_cores
            cu.input_staging = [str(input_file), str(crds)] + sd_shared_list
            cu.output_staging = st_out
        else:
            #old_coor = replicas[r].first_path + "/" + self.amber_coordinates
            replica_path = "/replica_%d_%d/" % (replica.id, 0)
            old_coor = "../staging_area/" + replica_path + self.amber_coordinates
            cu = radical.pilot.ComputeUnitDescription()
            cu.executable = self.amber_path
            cu.pre_exec = self.pre_exec
            cu.mpi = self.replica_mpi
            cu.arguments = ["-O", "-i ", input_file, 
                                  "-o ", output_file, 
                                  "-p ", self.amber_parameters, 
                                  "-c ", old_coor, 
                                  "-r ", new_coor, 
                                  "-x ", new_traj, 
                                  "-inf ", new_info]

            cu.cores = self.replica_cores
            cu.input_staging = [str(input_file)] + sd_shared_list
            cu.output_staging = st_out

        return cu

#-----------------------------------------------------------------------------------------------------------------------------------

    def prepare_replica_for_exchange(self, replicas, replica, sd_shared_list):
        """Creates a list of ComputeUnitDescription objects for exchange step on resource.
        Number of matrix_calculator_s2.py instances invoked on resource is equal to the number 
        of replicas. 

        Arguments:
        replicas - list of Replica objects

        Returns:
        exchange_replicas - list of radical.pilot.ComputeUnitDescription objects
        """
           
        # name of the file which contains swap matrix column data for each replica
        basename = self.inp_basename

        cu = radical.pilot.ComputeUnitDescription()
        cu.executable = "python"
        cu.input_staging  = sd_shared_list[3]
        cu.arguments = ["amber_matrix_calculator_pattern_b.py", replica.id, (replica.cycle-1), self.replicas, basename]
        cu.cores = 1
        cu.mpi = False
        
        return cu

    #--------------------------------------------------------------------------------
    # 
    def exchange_params(self, replica_1, replica_2):
        temp = replica_2.new_temperature
        replica_2.new_temperature = replica_1.new_temperature
        replica_1.new_temperature = temp

