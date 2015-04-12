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
from md_kernels.md_kernel_us import *
from kernels.kernels import KERNELS
from replicas.replica import ReplicaUS
import radical.utils.logger as rul
import amber_kernels_us.amber_matrix_calculator_pattern_b

#--------------------------------------------------------------------------------------------------------------

class AmberKernelUSPatternB(MdKernelUS):
    """This class is responsible for performing all operations related to Amber for RE scheme S2.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.

    RE pattern B:
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

        MdKernelUS.__init__(self, inp_file, work_dir_local)

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
        self.init_temperature = float(inp_file['input.MD']['init_temperature'])
        self.current_cycle = -1

        self.name = 'ak-patternB-us'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        self.shared_urls = []
        self.shared_files = []

    #-----------------------------------------------------------------------------------------
    # 
    def prepare_shared_data(self):

        parm_path = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_parameters
        inp_path  = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_input
        coor_path  = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_coordinates

        rstr_list = []
        for rstr in self.restraints_files:
            rstr_list.append(self.work_dir_local + "/" + rstr)

        calc_b = os.path.dirname(amber_kernels_us.amber_matrix_calculator_pattern_b.__file__)
        calc_b_path = calc_b + "/amber_matrix_calculator_pattern_b.py"

        self.shared_files.append(self.amber_parameters)
        self.shared_files.append(self.amber_input)
        self.shared_files.append(self.amber_coordinates)
        self.shared_files.append("amber_matrix_calculator_pattern_b.py")

        for rstr in self.restraints_files:
            self.shared_files.append(rstr)
        
        parm_url = 'file://%s' % (parm_path)
        self.shared_urls.append(parm_url)

        inp_url = 'file://%s' % (inp_path)
        self.shared_urls.append(inp_url)

        coor_url = 'file://%s' % (coor_path)
        self.shared_urls.append(coor_url)
 
        calc_b_url = 'file://%s' % (calc_b_path)
        self.shared_urls.append(calc_b_url)

        for rstr_p in rstr_list:
            rstr_url = 'file://%s' % (rstr_p)
            self.shared_urls.append(rstr_url)

    #-------------------------------------------------------------------------------------
    # 
    def build_restraint_file(self, replica):
        """Builds restraint file for replica, based on template file
        """

        template = self.work_dir_local + "/" + self.inp_folder + "/" + self.us_template
        r_file = open(template, "r")
        tbuffer = r_file.read()
        r_file.close()

        # hardcoded for now but can be arguments as well
        i = replica.id
        spacing = 10
        starting_value = 120 + i*spacing

        w_file = open(self.us_template+"."+str(i), "w")
        tbuffer = tbuffer.replace("@val1@", str(starting_value))
        tbuffer = tbuffer.replace("@val2@", str(starting_value+spacing))
        w_file.write(tbuffer)
        w_file.close()

    #-------------------------------------------------------------------------------------
    # 
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
        tbuffer = tbuffer.replace("@disang@",replica.new_restraints)
        tbuffer = tbuffer.replace("@temp@",str(self.init_temperature))
        
        replica.cycle += 1

        try:
            w_file = open(new_input_file, "w")
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            print 'Warning: unable to access file %s' % new_input_file

    #----------------------------------------------------------------------------------------------------------
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

        self.build_input_file(replica)

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

        cu = radical.pilot.ComputeUnitDescription()
        if replica.cycle == 1:
            # files needed to be moved in replica dir
            in_list = []
            for i in range(3):
                in_list.append(sd_shared_list[i])

            rid = replica.id
            in_list.append(sd_shared_list[rid+4])
 
            replica_path = "replica_%d_%d/" % (replica.id, 0)
            crds_out = {
                'source': self.amber_coordinates,
                'target': 'staging:///%s' % (replica_path + self.amber_coordinates),
                'action': radical.pilot.COPY
            }
            st_out.append(crds_out)

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
            cu.input_staging = [str(input_file)] + in_list
            cu.output_staging = st_out
        else:
            # files needed to be moved in replica dir
            in_list = []

            # restraint files are exchanged
            rid = int(replica.new_restraints[-1:])               
 
            in_list.append(sd_shared_list[0])
            in_list.append(sd_shared_list[1])
            in_list.append(sd_shared_list[rid+4])

            replica_path = "/replica_%d_%d/" % (replica.id, 0)
            old_coor = "../staging_area/" + replica_path + self.amber_coordinates

            cu.input_staging = [str(input_file)] + in_list
            cu.output_staging = st_out
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
            cu.input_staging = [str(input_file)] + in_list
            cu.output_staging = st_out

        return cu

    #------------------------------------------------------------------------------------------
    # 
    def prepare_replica_for_exchange(self, replica, sd_shared_list):
        """Creates a list of ComputeUnitDescription objects for exchange step on resource.
        Number of matrix_calculator_s2.py instances invoked on resource is equal to the number 
        of replicas. 

        Arguments:
        replicas - list of Replica objects

        Returns:
        exchange_replicas - list of radical.pilot.ComputeUnitDescription objects
        """
        all_restraints = ""
        for r in range(self.replicas):
            if r == 0:
                all_restraints = str(replica.new_restraints)
            else:
                all_restraints = all_restraints + " " + str(replica.new_restraints)

        all_restraints_list = all_restraints.split(" ")

        
        # name of the file which contains swap matrix column data for each replica
        basename = self.inp_basename

        cu = radical.pilot.ComputeUnitDescription()
        cu.pre_exec = self.pre_exec
        cu.executable = "python"
 
        in_list = []
        # copying calculator from staging area to cu filder
        in_list.append(sd_shared_list[3])
        rid = replica.id
        # copying .RST file for replica from staging area to cu folder
        in_list.append(sd_shared_list[rid+4])

        # copy new coordinates from MD run to CU directory
        coor_directive = {'source': 'staging:///%s' % replica.new_coor,
                          'target': replica.new_coor,
                          'action': radical.pilot.COPY
        }

        input_file = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_input

        data = {
            "replica_id": str(r),
            "replica_cycle" : str(replica.cycle-1),
            "replicas" : str(self.replicas),
            "base_name" : str(basename),
            "init_temp" : str(self.init_temperature),
            "amber_path" : str(self.amber_path),
            "amber_input" : str(self.amber_input),
            "amber_parameters": str(self.amber_parameters),
            "all_restraints" : all_restraints_list
        }

        dump_data = json.dumps(data)
        json_data = dump_data.replace("\\", "")
            
        cu.input_staging = [str(input_file)] + in_list + [coor_directive]
        cu.arguments = ["amber_matrix_calculator_pattern_b.py", json_data]
        cu.cores = 1            

        return cu


