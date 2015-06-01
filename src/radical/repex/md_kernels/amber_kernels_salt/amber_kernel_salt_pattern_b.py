"""
.. module:: radical.repex.md_kernles.amber_kernels_salt.amber_kernel_salt_pattern_b
.. moduleauthor::  <haoyuan.chen@rutgers.edu>
.. moduleauthor::  <antons.treikalis@rutgers.edu>
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
import radical.utils.logger as rul
from md_kernels.md_kernel_salt import *
from kernels.kernels import KERNELS
import amber_kernels_salt.amber_matrix_calculator_pattern_b

#-----------------------------------------------------------------------------------------------------------------------------------

class AmberKernelSaltPatternB(MdKernelSalt):
    """This class is responsible for performing all operations related to Amber for RE scheme S2.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.
    """
    def __init__(self, inp_file,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        MdKernelSalt.__init__(self, inp_file, work_dir_local)

        self.pre_exec = KERNELS[self.resource]["kernels"]["amber"]["pre_execution"]
        try:
            self.amber_path = inp_file['input.MD']['amber_path']
        except:
            print "Using default Amber path for %s" % inp_file['input.PILOT']['resource']
            try:
                self.amber_path = KERNELS[self.resource]["kernels"]["amber"]["executable"]
            except:
                print "Amber path for localhost is not defined..."

        self.amber_coordinates = inp_file['input.MD']['amber_coordinates']
        self.amber_parameters = inp_file['input.MD']['amber_parameters']
        self.amber_input = inp_file['input.MD']['amber_input']
        self.input_folder = inp_file['input.MD']['input_folder']

        self.shared_urls = []
        self.shared_files = []

        self.name = 'ak-patternB-sc'
        self.logger  = rul.getLogger ('radical.repex', self.name)

#-----------------------------------------------------------------------------------------------------------------------------------
    # OK
    def build_input_file(self, replica):
        """Builds input file for replica, based on template input file ala10.mdin
        """

        basename = self.inp_basename
            
        new_input_file = "%s_%d_%d.mdin" % (basename, replica.id, replica.cycle)
        outputname = "%s_%d_%d.mdout" % (basename, replica.id, replica.cycle)
        old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1))
        replica.new_coor = "%s_%d_%d.rst" % (basename, replica.id, replica.cycle)
        replica.new_traj = "%s_%d_%d.mdcrd" % (basename, replica.id, replica.cycle)
        replica.new_info = "%s_%d_%d.mdinfo" % (basename, replica.id, replica.cycle)

        if (replica.cycle == 0):
            first_step = 0
        elif (replica.cycle == 1):
            first_step = int(self.cycle_steps)
        else:
            first_step = (replica.cycle - 1) * int(self.cycle_steps)

        try:
            r_file = open( (os.path.join((self.work_dir_local + "/" + self.input_folder + "/"), self.amber_input)), "r")
        except IOError:
            print 'Warning: unable to access template file %s' % self.amber_input

        tbuffer = r_file.read()
        r_file.close()

        tbuffer = tbuffer.replace("@nstlim@",str(self.cycle_steps))
        tbuffer = tbuffer.replace("@salt@",str(float(replica.new_salt_concentration)))
        
        replica.cycle += 1

        try:
            w_file = open(new_input_file, "w")
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            print 'Warning: unable to access file %s' % new_input_file

    #-----------------------------------------------------------------------------------------------------------------------------------
    #
    def prepare_shared_data(self):
        """Creates a Compute Unit for shared data staging in
        these are Amber input files shared between all replicas
        """

        parm_path = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_parameters
        coor_path = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_coordinates
        inp_path  = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_input

        calc_b = os.path.dirname(amber_kernels_salt.amber_matrix_calculator_pattern_b.__file__)
        calc_b_path = calc_b + "/amber_matrix_calculator_pattern_b.py"

        self.shared_files.append(self.amber_parameters)
        self.shared_files.append(self.amber_coordinates)
        self.shared_files.append(self.amber_input)
        self.shared_files.append("amber_matrix_calculator_pattern_b.py")
        
        parm_url = 'file://%s' % (parm_path)
        self.shared_urls.append(parm_url)

        coor_url = 'file://%s' % (coor_path)
        self.shared_urls.append(coor_url)

        inp_url = 'file://%s' % (inp_path)
        self.shared_urls.append(inp_url)

        calc_b_url = 'file://%s' % (calc_b_path)
        self.shared_urls.append(calc_b_url)

    #-----------------------------------------------------------------------------------------------------------------------------------
    # 
    def prepare_replica_for_md(self, replica, sd_shared_list):
        """Prepares all replicas for execution. In this function are created CU descriptions for replicas, are
        specified input/output files to be transferred to/from target system. Note: input files for first and 
        subsequent simulation cycles are different.

        Arguments:
        replicas - list of Replica objects

        Returns:
        compute_replicas - list of radical.pilot.ComputeUnitDescription objects
        """
        
        # need to avoid this step!
        self.build_input_file(replica)
      
        crds = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_coordinates
        # in principle restraint file should be moved to shared directory
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
            cu.output_staging = st_out + [new_info]
        else:
            cu = radical.pilot.ComputeUnitDescription()
            replica_path = "/replica_%d_%d/" % (replica.id, 0)
            old_coor = "../staging_area/" + replica_path + self.amber_coordinates

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

            cu.input_staging = [str(input_file)] + sd_shared_list
            cu.output_staging = st_out + [new_info]

        return cu

    #-----------------------------------------------------------------------------------------------------------------------------------
    # 
    def prepare_replica_for_exchange(self, replicas, replica, sd_shared_list):
        """Creates a list of ComputeUnitDescription objects for exchange step on resource.
        Number of matrix_calculator_s2.py instances invoked on resource is equal to the number 
        of replicas. 

        Arguments:
        replicas - list of Replica objects

        Returns:
        exchange_replicas - list of radical.pilot.ComputeUnitDescription objects
        """
        all_salt = ""
        for r in range(len(replicas)):
            if r == 0:
                all_salt = str(replica.new_salt_concentration)
            else:
                all_salt = all_salt + " " + str(replica.new_salt_concentration)

        all_salt_list = all_salt.split(" ")

        # name of the file which contains swap matrix column data for each replica
        matrix_col = "matrix_column_%s_%s.dat" % ((replica.cycle-1), replica.id)
        basename = self.inp_basename

        new_coor = replica.new_coor
        sd_new_coor = {'source': 'staging:///%s' % new_coor,
                       'target': new_coor,
                       'action': radical.pilot.COPY
        }

        cu = radical.pilot.ComputeUnitDescription()
        cu.pre_exec = self.pre_exec
        cu.executable = "python"
            
        input_file = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_input

        data = {
            "replica_id": str(replica.id),
            "replica_cycle" : str(replica.cycle-1),
            "replicas" : str(len(replicas)),
            "base_name" : str(basename),
            "init_temp" : str(self.init_temperature),
            "amber_path" : str(self.amber_path),
            "amber_input" : str(self.amber_input),
            "amber_parameters": str(self.amber_parameters),
            "all_salt_ctr" : all_salt,
            "new_coor" : str(replica.new_coor)
        }

        dump_data = json.dumps(data)
        json_data = dump_data.replace("\\", "")
        cu.input_staging  = [sd_shared_list[2], sd_shared_list[3]] + [sd_new_coor]
        cu.output_staging = matrix_col
        cu.arguments = ["amber_matrix_calculator_pattern_b.py", json_data]
        cu.cores = 1            

        return cu
        
