"""
.. module:: radical.repex.md_kernles.amber_kernels_salt.kernel_pattern_s_salt
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
import operator
import datetime
from os import path
import radical.pilot
import radical.utils.logger as rul
from kernels.kernels import KERNELS
from replicas.replica import Replica1d
import amber_kernels_salt.input_file_builder
import amber_kernels_salt.salt_conc_pre_exec
import amber_kernels_salt.salt_conc_post_exec
import amber_kernels_salt.global_ex_calculator

#-------------------------------------------------------------------------------

class KernelPatternSsalt(object):
    
    def __init__(self, inp_file, rconfig,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as 
        specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        self.name = 'ak-patternB-sc'
        self.ex_name = 'salt-concentration'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        self.resource          = rconfig['target'].get('resource')
        self.inp_basename      = inp_file['remd.input'].get('input_file_basename')
        self.input_folder      = inp_file['remd.input'].get('input_folder')
        self.us_template       = inp_file['remd.input'].get('us_template') 
        self.amber_parameters  = inp_file['remd.input'].get('amber_parameters')
        self.amber_coordinates = inp_file['remd.input'].get('amber_coordinates')
        self.amber_input       = inp_file['remd.input'].get('amber_input')
        self.work_dir_local    = work_dir_local
        self.current_cycle     = -1

        self.cores         = int(rconfig['target'].get('cores', '1'))
        self.replicas      = int(inp_file['remd.input'].get('number_of_replicas'))
        self.cycle_steps   = int(inp_file['remd.input'].get('steps_per_cycle'))
        self.nr_cycles     = int(inp_file['remd.input'].get('number_of_cycles','1'))
        self.replica_cores = int(inp_file['remd.input'].get('replica_cores', '1'))
        self.nr_ex_neighbors = int(inp_file['remd.input'].get('nr_exchange_neighbors', '1'))

        self.min_salt         = float(inp_file['remd.input'].get('min_salt'))
        self.max_salt         = float(inp_file['remd.input'].get('max_salt'))
        self.init_temperature = float(inp_file['remd.input'].get('init_temperature'))

        #-----------------------------------------------------------------------

        if inp_file['remd.input'].get('replica_mpi') == "True":
            self.replica_mpi = True
        else:
            self.replica_mpi = False

        if inp_file['remd.input'].get('download_mdinfo') == 'True':
            self.down_mdinfo = True
        else:
            self.down_mdinfo = False

        if inp_file['remd.input'].get('download_mdout') == 'True':
            self.down_mdout = True
        else:
            self.down_mdout = False

        if inp_file['remd.input'].get('exchange_off') == "True":
            self.exchange_off = True
        else:
            self.exchange_off = False

        self.amber_path = inp_file['remd.input'].get('amber_path')
        if self.amber_path == None:
            self.logger.info("Using default Amber path for: {0}".format(rconfig['target'].get('resource')))
            self.amber_path = KERNELS[self.resource]["kernels"]["amber"].get("executable")
            self.amber_path_mpi = KERNELS[self.resource]["kernels"]["amber"].get("executable_mpi")
        if self.amber_path == None:
            self.logger.info("Amber (sander) path can't be found, looking for sander.MPI")
            if self.amber_path_mpi == None:
                self.logger.info("Amber (sander.MPI) path can't be found, exiting...")
            sys.exit(1)

        self.pre_exec = KERNELS[self.resource]["kernels"]["amber"]["pre_execution"]

        self.shared_urls = []
        self.shared_files = []

        self.salt_dict = {}

    #---------------------------------------------------------------------------
    #
    def prepare_shared_data(self, replicas):

        parm_path = self.work_dir_local + "/" + self.input_folder + "/" + \
                    self.amber_parameters
        coor_path = self.work_dir_local + "/" + self.input_folder + "/" + \
                    self.amber_coordinates
                    
        input_template = self.inp_basename[:-5] + ".mdin"
        input_template_path = self.work_dir_local + "/" + \
                              self.input_folder + "/" + \
                              input_template

        build_inp = os.path.dirname(amber_kernels_salt.input_file_builder.__file__)
        build_inp_path = build_inp + "/input_file_builder.py"

        global_calc = os.path.dirname(amber_kernels_salt.global_ex_calculator.__file__)
        global_calc_path = global_calc + "/global_ex_calculator.py"

        salt_pre_exec = os.path.dirname(amber_kernels_salt.salt_conc_pre_exec.__file__)
        salt_pre_exec_path = salt_pre_exec + "/salt_conc_pre_exec.py"

        salt_post_exec = os.path.dirname(amber_kernels_salt.salt_conc_post_exec.__file__)
        salt_post_exec_path = salt_post_exec + "/salt_conc_post_exec.py"
        #-----------------------------------------------------------------------
        self.shared_files.append(self.amber_parameters)
        self.shared_files.append(self.amber_coordinates)
        self.shared_files.append(input_template)
        self.shared_files.append("input_file_builder.py")
        self.shared_files.append("global_ex_calculator.py")
        self.shared_files.append("salt_conc_pre_exec.py")
        self.shared_files.append("salt_conc_post_exec.py")

        parm_url = 'file://%s' % (parm_path)
        self.shared_urls.append(parm_url)  

        coor_url = 'file://%s' % (coor_path)
        self.shared_urls.append(coor_url)   

        inp_url = 'file://%s' % (input_template_path)
        self.shared_urls.append(inp_url)

        build_inp_url = 'file://%s' % (build_inp_path)
        self.shared_urls.append(build_inp_url)

        global_calc_url = 'file://%s' % (global_calc_path)
        self.shared_urls.append(global_calc_url)

        salt_pre_exec_url = 'file://%s' % (salt_pre_exec_path)
        self.shared_urls.append(salt_pre_exec_url)

        salt_post_exec_url = 'file://%s' % (salt_post_exec_path)
        self.shared_urls.append(salt_post_exec_url)

    #---------------------------------------------------------------------------
    #
    def initialize_replicas(self):
        """Initializes replicas and their attributes to default values

           Changed to use geometrical progression for temperature assignment.
        """
        replicas = []
        N = self.replicas
        for k in range(N):
            new_salt = (self.max_salt-self.min_salt)/(N-1)*k + self.min_salt
            r = Replica1d(k, new_salt_concentration=new_salt)
            replicas.append(r)
            self.salt_dict[r.id] = r.new_salt_concentration
            
        return replicas

    #---------------------------------------------------------------------------
    # 
    def prepare_replica_for_md(self, replica, sd_shared_list):
        """Prepares all replicas for execution. In this function are created CU 
        descriptions for replicas, are
        specified input/output files to be transferred to/from target system. 
        Note: input files for first and 
        subsequent simulation cycles are different.

        Arguments:
        replicas - list of Replica objects

        Returns:
        compute_replicas - list of radical.pilot.ComputeUnitDescription objects
        """

        basename = self.inp_basename
        template = self.inp_basename[:-5] + ".mdin"
            
        new_input_file = "%s_%d_%d.mdin" % (basename, replica.id, replica.cycle)
        outputname = "%s_%d_%d.mdout" % (basename, replica.id, replica.cycle)
        old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1))
        replica.new_coor = "%s_%d_%d.rst"    % (basename, replica.id, \
                                                replica.cycle)
        replica.new_traj = "%s_%d_%d.mdcrd"  % (basename, replica.id, \
                                                replica.cycle)
        replica.new_info = "%s_%d_%d.mdinfo" % (basename, replica.id, \
                                                replica.cycle)
        replica.old_coor = old_name + ".rst"

        if (replica.cycle == 0):
            first_step = 0
        elif (replica.cycle == 1):
            first_step = int(self.cycle_steps)
        else:
            first_step = (replica.cycle - 1) * int(self.cycle_steps)

        #-----------------------------------------------------------------------

        input_file = "%s_%d_%d.mdin" % (self.inp_basename, \
                                        replica.id, \
                                       (replica.cycle))
        output_file = "%s_%d_%d.mdout" % (self.inp_basename, \
                                          replica.id, \
                                         (replica.cycle))

        new_coor = replica.new_coor
        new_traj = replica.new_traj
        new_info = replica.new_info

        old_coor = replica.old_coor
        old_traj = replica.old_traj

        crds = self.work_dir_local + "/" + \
               self.input_folder + "/" + self.amber_coordinates
        parm = self.work_dir_local + "/" + \
               self.input_folder + "/" + self.amber_parameters

        data = {
            "cycle_steps": str(self.cycle_steps),
            "new_salt_concentration" : str(replica.new_salt_concentration),
            "amber_input" : str(template),
            "new_input_file" : str(new_input_file),
            "cycle" : str(replica.cycle)
                }
        dump_pre_data = json.dumps(data)
        json_pre_data_bash = dump_pre_data.replace("\\", "")
        json_pre_data_sh = dump_pre_data.replace("\"", "\\\\\"")

        replica.cycle += 1

        #-----------------------------------------------------------------------
        
        stage_out = []
        stage_in = []

        if self.down_mdinfo == True:
            info_local = {
                'source':   new_info,
                'target':   new_info,
                'action':   radical.pilot.TRANSFER
            }
            stage_out.append(info_local)

        if self.down_mdout == True:
            output_local = {
                'source':   output_file,
                'target':   output_file,
                'action':   radical.pilot.TRANSFER
            }
            stage_out.append(output_local)


        info_out = {
            'source': new_info,
            'target': 'staging:///%s' % new_info,
            'action': radical.pilot.COPY
        }
        stage_out.append(info_out)

        coor_out = {
            'source': new_coor,
            'target': 'staging:///%s' % new_coor,
            'action': radical.pilot.COPY
        }
        stage_out.append(coor_out)

        cu = radical.pilot.ComputeUnitDescription()

        if KERNELS[self.resource]["shell"] == "bourne":
            pre_exec_str = "python input_file_builder.py " + "\'" + json_pre_data_sh + "\'"
            cu.executable = '/bin/sh'
        elif KERNELS[self.resource]["shell"] == "bash":
            pre_exec_str = "python input_file_builder.py " + "\'" + json_pre_data_bash + "\'"
            cu.executable = '/bin/bash'          

        if replica.cycle == 1:       
            
            amber_str = self.amber_path
            argument_str = " -O " + " -i " + new_input_file + \
                           " -o " + output_file + \
                           " -p " +  self.amber_parameters + \
                           " -c " + self.amber_coordinates + \
                           " -r " + new_coor + \
                           " -x " + new_traj + \
                           " -inf " + new_info  

            crds_out = {
                'source': self.amber_coordinates,
                'target': 'staging:///%s' % (self.amber_coordinates),
                'action': radical.pilot.COPY
            }
            stage_out.append(crds_out)

            # files needed to be staged in replica dir
            for i in range(4):
                stage_in.append(sd_shared_list[i])
                
            cu.pre_exec = self.pre_exec
            cu.arguments = ['-c', pre_exec_str + "; " + amber_str + argument_str]                                   
            cu.mpi = self.replica_mpi
            cu.cores          = self.replica_cores
            cu.input_staging  = stage_in
            cu.output_staging = stage_out
        else:
            old_coor = "../staging_area/" + self.amber_coordinates

            amber_str = self.amber_path
            argument_str = " -O " + " -i " + new_input_file + \
                           " -o " + output_file + \
                           " -p " +  self.amber_parameters + \
                           " -c " + old_coor + \
                           " -r " + new_coor + \
                           " -x " + new_traj + \
                           " -inf " + new_info

            replica_path = "/replica_%d_%d/" % (replica.id, 0)

            # files needed to be staged in replica dir
            for i in range(4):
                stage_in.append(sd_shared_list[i])

            cu.pre_exec = self.pre_exec
            cu.arguments = ['-c', pre_exec_str + "; " + amber_str + argument_str]   
            cu.mpi = self.replica_mpi
            cu.cores = self.replica_cores
            cu.input_staging = stage_in
            cu.output_staging = stage_out

        return cu

    #---------------------------------------------------------------------------
    # 
    def prepare_replica_for_exchange(self, replicas, replica, sd_shared_list):
        """Creates a list of ComputeUnitDescription objects for exchange step 
        on resource.
        Number of matrix_calculator_s2.py instances invoked on resource is equal 
        to the number 
        of replicas. 

        Arguments:
        replicas - list of Replica objects

        Returns:
        exchange_replicas - list of radical.pilot.ComputeUnitDescription objects
        """

        # name of the file which contains swap matrix column data for each replica
        basename = self.inp_basename
        matrix_col = "matrix_column_%s_%s.dat" % (str(replica.id), str(replica.cycle-1))

        salts_sorted = sorted(self.salt_dict.items(), key=operator.itemgetter(1))

        count = 0
        for item in salts_sorted:
            if item[0] == replica.id:
                idx = count
            else:
                count += 1

        group_salts = {}
        rid  = salts_sorted[idx][0]
        salt = salts_sorted[idx][1]
        group_salts[str(rid)] = str(salt)
        for i in range(self.nr_ex_neighbors):
            if (idx+i+1) < len(replicas):
                rid  = salts_sorted[idx+i+1][0]
                salt = salts_sorted[idx+i+1][1]
                group_salts[str(rid)] = str(salt)
            if (idx-i-1) >= 0:
                rid  = salts_sorted[idx-i-1][0]
                salt = salts_sorted[idx-i-1][1]
                group_salts[str(rid)] = str(salt)

        cu = radical.pilot.ComputeUnitDescription()
        
        data = {
            "replica_id": str(replica.id),
            "replica_cycle" : str(replica.cycle-1),
            "replicas" : str(self.replicas),
            "base_name" : str(basename),
            "init_temp" : str(self.init_temperature),
            "init_salt" : str(replica.new_salt_concentration),
            "amber_path" : str(self.amber_path),
            "amber_input" : str(self.amber_input),
            "all_salts" : group_salts, 
            "amber_parameters": str(self.amber_parameters), 
            "r_old_path": str(replica.old_path),
        }

        dump_data = json.dumps(data)
        json_data = dump_data.replace("\\", "")

        salt_pre_exec = ["python salt_conc_pre_exec.py " + "\'" + json_data + "\'"]
        cu.pre_exec = self.pre_exec + salt_pre_exec
        cu.executable = self.amber_path_mpi
        salt_post_exec = ["python salt_conc_post_exec.py " + "\'" + json_data + "\'"]
        cu.post_exec = salt_post_exec

        rid = replica.id
        in_list = []
        in_list.append(sd_shared_list[0])
        in_list.append(sd_shared_list[2])
        in_list.append(sd_shared_list[5])
        in_list.append(sd_shared_list[6])
  
        cu.input_staging = in_list

        out_list = []
        matrix_col_out = {
            'source': matrix_col,
            'target': 'staging:///%s' % (matrix_col),
            'action': radical.pilot.COPY
        }
        out_list.append(matrix_col_out)

        cu.arguments = ['-ng', str(len(group_salts)), '-groupfile', 'groupfile']
        cu.cores = len(group_salts)
        cu.mpi = True
        cu.output_staging = out_list   

        return cu

    #---------------------------------------------------------------------------
    #
    def prepare_global_ex_calc(self, GL, current_cycle, replicas, sd_shared_list):

        stage_out = []
        stage_in = []

        if GL == 1:
            cycle = replicas[0].cycle-1
        else:
            cycle = replicas[0].cycle
        
        # global_ex_calculator.py file
        stage_in.append(sd_shared_list[4])

        outfile = "pairs_for_exchange_{cycle}.dat".format(cycle=cycle)
        stage_out.append(outfile)

        cu = radical.pilot.ComputeUnitDescription()
        cu.pre_exec = self.pre_exec
        cu.executable = "python"
        cu.input_staging  = stage_in
        cu.arguments = ["global_ex_calculator.py", str(self.replicas), str(cycle)]
        cu.cores = 1
        cu.mpi = False            
        cu.output_staging = stage_out

        return cu

    #---------------------------------------------------------------------------
    #
    def perform_swap(self, replica_i, replica_j):
        """Performs an exchange of salt concentrations

        Arguments:
        replica_i - a replica object
        replica_j - a replica object
        """

        # swap temperatures
        temp_j = replica_j.new_salt_concentration
        temp_i = replica_i.new_salt_concentration

        replica_j.new_salt_concentration = temp_i
        replica_i.new_salt_concentration = temp_j
        # record that swap was performed
        replica_i.swap = 1
        replica_j.swap = 1

        self.salt_dict[replica_j.id] = temp_i
        self.salt_dict[replica_i.id] = temp_j

    #---------------------------------------------------------------------------
    #
    def do_exchange(self, current_cycle, replicas):
        """
        """

        r1 = None
        r2 = None

        cycle = replicas[0].cycle-1

        infile = "pairs_for_exchange_{cycle}.dat".format(cycle=cycle)
        try:
            f = open(infile)
            lines = f.readlines()
            f.close()
            for l in lines:
                pair = l.split()
                r1_id = int(pair[0])
                r2_id = int(pair[1])
                for r in replicas:
                    if r.id == r1_id:
                        r1 = r
                    if r.id == r2_id:
                        r2 = r
                #---------------------------------------------------------------
                # guard
                if r1 == None:
                    rid = random.randint(0,(len(replicas)-1))
                    r1 = replicas[rid]
                if r2 == None:
                    rid = random.randint(0,(len(replicas)-1))
                    r2 = replicas[rid]
                #---------------------------------------------------------------

                # swap parameters
                self.perform_swap(r1, r2)
                r1.swap = 1
                r2.swap = 1
        except:
            raise

