"""
.. module:: radical.repex.md_kernles.amber_kernels_us.kernel_pattern_s_us
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
from os import listdir
from os.path import isfile, join
import radical.utils.logger as rul
from replicas.replica import Replica1d
from kernels.kernels import KERNELS
import amber_kernels_us.input_file_builder
import amber_kernels_us.global_ex_calculator
#import amber_kernels_us.global_ex_calculator_mpi
import amber_kernels_us.ind_ex_calculator

#-------------------------------------------------------------------------------

class KernelPatternSus(object):
    """

    """
    def __init__(self, inp_file, rconfig, work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as 
        specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        self.resource = rconfig['target']['resource']
        self.inp_basename = inp_file['remd.input']['input_file_basename']
        self.input_folder = inp_file['remd.input']['input_folder']
        self.replicas = int(inp_file['remd.input']['number_of_replicas'])
        self.cores = int(rconfig['target']['cores'])
        self.us_template = inp_file['remd.input']['us_template']                           
        self.init_temperature = float(inp_file['remd.input']['init_temperature'])
        self.cycle_steps = int(inp_file['remd.input']['steps_per_cycle'])
        self.work_dir_local = work_dir_local
        
        try:
            self.nr_cycles = int(inp_file['remd.input']['number_of_cycles'])
        except:
            self.nr_cycles = None

        if 'replica_mpi' in inp_file['remd.input']:
            mpi = inp_file['remd.input']['replica_mpi']
            if mpi == "True":
                self.replica_mpi = True
            else:
                self.replica_mpi = False
        else:
            self.replica_mpi = False

        if 'exchange_mpi' in inp_file['remd.input']:
            mpi = inp_file['remd.input']['exchange_mpi']
            if mpi == "True":
                self.exchange_mpi = True
            else:
                self.exchange_mpi = False
        else:
            self.exchange_mpi = False
            
        if 'download_mdinfo' in inp_file['remd.input']:
            if inp_file['remd.input']['download_mdinfo'] == 'True':
                self.down_mdinfo = True
            else:
                self.down_mdinfo = False
        else:
            self.down_mdinfo = True

        if 'download_mdout' in inp_file['remd.input']:
            if inp_file['remd.input']['download_mdout'] == 'True':
                self.down_mdout = True
            else:
                self.down_mdout = False
        else:
            self.down_mdout = True

        try:
            self.replica_cores = inp_file['remd.input']['replica_cores']
        except:
            self.replica_cores = 1

        self.restraints_files = []
        for k in range(self.replicas):
            self.restraints_files.append(self.us_template + "." + str(k) )

        self.pre_exec = KERNELS[self.resource]["kernels"]["amber"]["pre_execution"]
        try:
            self.amber_path = inp_file['remd.input']['amber_path']
        except:
            print "Using default Amber path for %s" % rconfig['target']['resource']
            try:
                self.amber_path = KERNELS[self.resource]["kernels"]["amber"]["executable"]
            except:
                print "Amber path for localhost is not defined..."

        self.amber_coordinates_path = inp_file['remd.input']['amber_coordinates_folder']
        if 'same_coordinates' in inp_file['remd.input']:
            coors = inp_file['remd.input']['same_coordinates']
            if coors == "True":
                self.same_coordinates = True
            else:
                self.same_coordinates = False
        else:
            self.same_coordinates = True

        self.amber_parameters = inp_file['remd.input']['amber_parameters']
        self.amber_input = inp_file['remd.input']['amber_input']
        self.input_folder = inp_file['remd.input']['input_folder']
        self.us_start_param = float(inp_file['remd.input']['us_start_param'])
        self.us_end_param = float(inp_file['remd.input']['us_end_param'])
        self.current_cycle = -1
        self.name = 'ak-us-patternB'
        self.ex_name = 'umbrella_sampling'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        self.shared_urls = []
        self.shared_files = []

    #---------------------------------------------------------------------------
    #
    def initialize_replicas(self):
        """Initializes replicas and their attributes to default values

           Changed to use geometrical progression for temperature assignment.

           The user needs to provide the indexed restraint files now. A script 
           that generates those files will be provided later.
        """
        replicas = []

        #-----------------------------------------------------------------------
        # parse coor file
        coor_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_coordinates_path
        coor_list  = listdir(coor_path)
        base = coor_list[0]

        self.coor_basename = base.split('inpcrd')[0]+'inpcrd'
        #-----------------------------------------------------------------------
        # 
        for k in range(self.replicas):

            spacing = (self.us_end_param - self.us_start_param) / (float(self.replicas)-1)
            starting_value = self.us_start_param + k*spacing

            rstr_val_1 = str(starting_value)

            if self.same_coordinates == False:
                coor_file = self.coor_basename + ".0." + str(k)
                r = Replica1d(k, new_restraints=self.restraints_files[k], \
                             rstr_val_1=float(rstr_val_1), \
                             coor=coor_file, \
                             indx1=0, \
                             indx2=k)
            else:
                coor_file = self.coor_basename + ".0.0"
                r = Replica1d(k, new_restraints=self.restraints_files[k], \
                                 rstr_val_1=float(rstr_val_1), \
                                 coor=coor_file)

            replicas.append(r)
            
        return replicas

    #---------------------------------------------------------------------------
    # 
    def prepare_shared_data(self, replicas):

        parm_path = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_parameters
        coor_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_coordinates_path
        inp_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_input

        build_inp = os.path.dirname(amber_kernels_us.input_file_builder.__file__)
        build_inp_path = build_inp + "/input_file_builder.py"

        global_calc = os.path.dirname(amber_kernels_us.global_ex_calculator.__file__)
        global_calc_path = global_calc + "/global_ex_calculator.py"

        rstr_template_path = self.work_dir_local + "/" + self.input_folder + "/" + self.us_template

        global_calc_s = os.path.dirname(amber_kernels_us.global_ex_calculator.__file__)
        global_calc_path_s = global_calc_s + "/global_ex_calculator.py"

        ind_calc = os.path.dirname(amber_kernels_us.ind_ex_calculator.__file__)
        ind_calc_path = ind_calc + "/ind_ex_calculator.py"
        #-----------------------------------------------------------------------

        self.shared_files.append(self.amber_parameters)
        self.shared_files.append(self.amber_input)
        self.shared_files.append("input_file_builder.py")
        self.shared_files.append("global_ex_calculator.py")
        self.shared_files.append(self.us_template)
        self.shared_files.append("global_ex_calculator.py")
        self.shared_files.append("ind_ex_calculator.py")

        if self.same_coordinates == False:
            for repl in replicas:
                self.shared_files.append(repl.coor_file)
        else:
            self.shared_files.append(replicas[0].coor_file)
        #-----------------------------------------------------------------------

        parm_url = 'file://%s' % (parm_path)
        self.shared_urls.append(parm_url)

        inp_url = 'file://%s' % (inp_path)
        self.shared_urls.append(inp_url)

        build_inp_url = 'file://%s' % (build_inp_path)
        self.shared_urls.append(build_inp_url)

        global_calc_url = 'file://%s' % (global_calc_path)
        self.shared_urls.append(global_calc_url)

        rstr_template_url = 'file://%s' % (rstr_template_path)
        self.shared_urls.append(rstr_template_url)

        global_calc_url_s = 'file://%s' % (global_calc_path_s)
        self.shared_urls.append(global_calc_url_s)

        ind_calc_url = 'file://%s' % (ind_calc_path)
        self.shared_urls.append(ind_calc_url)

        if self.same_coordinates == False:
            for repl in replicas:
                cf_path = join(coor_path,repl.coor_file)
                coor_url = 'file://%s' % (cf_path)
                self.shared_urls.append(coor_url)
        else:
            cf_path = join(coor_path,replicas[0].coor_file)
            coor_url = 'file://%s' % (cf_path)
            self.shared_urls.append(coor_url)

    #---------------------------------------------------------------------------
    # 
    def prepare_replica_for_md(self, replica, sd_shared_list):
 
        basename = self.inp_basename
            
        new_input_file = "%s_%d_%d.mdin" % (basename, replica.id, replica.cycle)
        outputname = "%s_%d_%d.mdout" % (basename, replica.id, replica.cycle)
        old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1))

        replica.new_coor = "%s_%d_%d.rst" % (basename, replica.id, replica.cycle)
        replica.new_traj = "%s_%d_%d.mdcrd" % (basename, replica.id, replica.cycle)
        replica.new_info = "%s_%d_%d.mdinfo" % (basename, replica.id, replica.cycle)

        replica.old_coor = old_name + ".rst"

        if (replica.cycle == 0):
            first_step = 0
        elif (replica.cycle == 1):
            first_step = int(self.cycle_steps)
        else:
            first_step = (replica.cycle - 1) * int(self.cycle_steps)

        replica.cycle += 1
        #-----------------------------------------------------------------------  

        input_file = "%s_%d_%d.mdin" % (self.inp_basename, replica.id, (replica.cycle-1))
        output_file = "%s_%d_%d.mdout" % (self.inp_basename, replica.id, (replica.cycle-1))

        stage_out = []
        stage_in = []

        new_coor = replica.new_coor
        new_traj = replica.new_traj
        new_info = replica.new_info
        old_coor = replica.old_coor
        rid = replica.id

        replica_path = "replica_%d/" % (rid)

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

        new_coor_out = {
            'source': new_coor,
            'target': 'staging:///%s' % (replica_path + new_coor),
            'action': radical.pilot.COPY
        }
        stage_out.append(new_coor_out)
        #-----------------------------------------------------------------------
         
        info_out = {
                'source': new_info,
                'target': 'staging:///%s' % (replica_path + new_info),
                'action': radical.pilot.COPY
            }
        stage_out.append(info_out)

        data = {
            "cycle_steps": str(self.cycle_steps),
            "new_restraints" : str(replica.new_restraints),
            "new_temperature" : str(self.init_temperature),
            "amber_input" : str(self.amber_input),
            "new_input_file" : str(new_input_file),
            "us_template": str(self.us_template),
            "cycle" : str(replica.cycle),
            "rstr_val_1" : str(replica.rstr_val_1)
                }
        dump_pre_data = json.dumps(data)

        json_pre_data_bash = dump_pre_data.replace("\\", "")
        json_pre_data_sh = dump_pre_data.replace("\"", "\\\\\"")

        #-----------------------------------------------------------------------
        # umbrella sampling
        data = {
            "replica_id": str(rid),
            "replica_cycle" : str(replica.cycle-1),
            "replicas" : str(self.replicas),
            "base_name" : str(basename),
            "init_temp" : str(replica.new_temperature),
            "amber_input" : str(self.amber_input),
            "amber_parameters": str(self.amber_parameters),
            "new_restraints" : str(replica.new_restraints)
        }
        dump_data = json.dumps(data)
        json_post_data_us = dump_data.replace("\\", "")

        #-----------------------------------------------------------------------

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
                           " -c " + replica.coor_file + \
                           " -r " + new_coor + \
                           " -x " + new_traj + \
                           " -inf " + new_info  

            restraints_out = replica.new_restraints
            restraints_out_st = {
                'source': (replica.new_restraints),
                'target': 'staging:///%s' % (replica.new_restraints),
                'action': radical.pilot.COPY
            }
            stage_out.append(restraints_out_st)

            #-------------------------------------------------------------------
            # files needed to be staged in replica dir
            for i in range(3):
                stage_in.append(sd_shared_list[i])

            # us template
            stage_in.append(sd_shared_list[4])

            #-------------------------------------------------------------------            
            # replica coor
            repl_coor = replica.coor_file

            # index of replica_coor
            c_index = self.shared_files.index(repl_coor) 
            stage_in.append(sd_shared_list[c_index])

            #-------------------------------------------------------------------
            cu.pre_exec = self.pre_exec
            cu.arguments = ['-c', pre_exec_str + "; " + amber_str + argument_str]  
            cu.cores = self.replica_cores
            cu.input_staging = stage_in
            cu.output_staging = stage_out
            cu.mpi = self.replica_mpi
            
        else:
            amber_str = self.amber_path
            argument_str = " -O " + " -i " + new_input_file + " -o " + output_file + \
                           " -p " +  self.amber_parameters + " -c " + old_coor + \
                           " -r " + new_coor + " -x " + new_traj + " -inf " + new_info
            
            # parameters file
            stage_in.append(sd_shared_list[0])

            # base input file ala10_us.mdin
            stage_in.append(sd_shared_list[1])

            # input_file_builder.py
            stage_in.append(sd_shared_list[2])
            #-------------------------------------------------------------------
            # restraint file
            restraints_in_st = {'source': 'staging:///%s' % replica.new_restraints,
                                'target': replica.new_restraints,
                                'action': radical.pilot.COPY
            }
            stage_in.append(restraints_in_st)

            old_coor_st = {'source': 'staging:///%s' % (replica_path + old_coor),
                           'target': (old_coor),
                           'action': radical.pilot.COPY
            }
            stage_in.append(old_coor_st)

            new_coor_out = {
                    'source': new_coor,
                    'target': 'staging:///%s' % (replica_path + new_coor),
                    'action': radical.pilot.COPY
                }
            stage_out.append(new_coor_out)

            cu.pre_exec = self.pre_exec
            cu.arguments = ['-c', pre_exec_str + "; " + amber_str + argument_str] 
            cu.input_staging = stage_in
            cu.output_staging = stage_out
            cu.cores = self.replica_cores
            cu.mpi = self.replica_mpi

        return cu

    #---------------------------------------------------------------------------
    #
    def prepare_replica_for_exchange(self, replicas, replica, sd_shared_list):
           
        basename  = self.inp_basename
        matrix_col = "matrix_column_%s_%s.dat" % (str(replica.id), str(replica.cycle-1))

        stage_out = []
        col_out = {
            'source': matrix_col,
            'target': 'staging:///%s' % matrix_col,
            'action': radical.pilot.COPY
        }
        stage_out.append(col_out)

        all_restraints = []
        for r in replicas:
            all_restraints.append(str(r.new_restraints))

        data = {
            "replica_id": str(replica.id),
            "replica_cycle" : str(replica.cycle-1),
            "replicas" : str(self.replicas),
            "base_name" : str(basename),
            "init_temp" : str(self.init_temperature),
            "new_restraints" : str(replica.new_restraints),
            "amber_path" : str(self.amber_path),
            "amber_input" : str(self.amber_input),
            "all_restraints" : all_restraints
        }
        dump_data = json.dumps(data)
        json_data = dump_data.replace("\\", "")

        """
        rid = replica.id
        data = {
            "replica_id": str(rid),
            "replica_cycle" : str(replica.cycle-1),
            "replicas" : str(self.replicas),
            "base_name" : str(basename),
            "init_temp" : str(replica.new_temperature),
            "new_restraints" : str(replica.new_restraints)
        }
        dump_data = json.dumps(data)
        json_post_data_us_bash = dump_data.replace("\\", "")
        json_post_data_us_sh   = dump_data.replace("\"", "\\\\\"")
        """

        cu = radical.pilot.ComputeUnitDescription()
        cu.executable = "python"
        cu.input_staging  = sd_shared_list[6]
        cu.output_staging = stage_out
        #cu.arguments = ["ind_ex_calculator.py", replica.id, (replica.cycle-1), self.replicas, basename, replica.new_temperature, replica.new_restraints]
        cu.arguments = ["ind_ex_calculator.py", json_data]
        cu.cores = 1
        cu.mpi = False
        
        return cu

    #---------------------------------------------------------------------------
    #
    def prepare_global_ex_calc(self, GL, current_cycle, replicas, sd_shared_list):

        stage_out = []
        stage_in = []

        cycle = replicas[0].cycle-1

        outfile = "pairs_for_exchange_{cycle}.dat".format(cycle=cycle)
        stage_out.append(outfile)

        all_restraints = {}
        all_temperatures = {}
        for repl in replicas:
            all_restraints[str(repl.id)] = str(repl.new_restraints)
            all_temperatures[str(repl.id)] = str(repl.new_temperature)

        data = {
            "current_cycle" : str(cycle),
            "replicas" : str(self.replicas),
            "base_name" : str(self.inp_basename),
            "all_temperatures" : all_temperatures,
            "all_restraints" : all_restraints
        }
        dump_data = json.dumps(data)
        json_data_us = dump_data.replace("\\", "")

        # so that Ioannis can't use it!
        """
        if self.exchange_mpi == True:
            # global_ex_calculator_mpi.py file
            stage_in.append(sd_shared_list[3])

            cu = radical.pilot.ComputeUnitDescription()
            cu.pre_exec = self.pre_exec
            cu.executable = "python"
            cu.input_staging  = stage_in
            cu.arguments = ["global_ex_calculator_mpi.py", json_data_us]

            if self.replicas > 999:
                self.cores = self.replicas / 2
            elif self.cores < self.replicas:
                if (self.replicas % self.cores) != 0:
                    self.logger.info("Number of replicas must be divisible by the number of Pilot cores!")
                    self.logger.info("pilot cores: {0}; replicas {1}".format(self.cores, self.replicas))
                    sys.exit()
                else:
                    cu.cores = self.cores
            elif self.cores >= self.replicas:
                cu.cores = self.replicas
            else:
                self.logger.info("Number of replicas must be divisible by the number of Pilot cores!")
                self.logger.info("pilot cores: {0}; replicas {1}".format(self.cores, self.replicas))
                sys.exit()
            cu.mpi = True         
            cu.output_staging = stage_out
        else:
        """

        # global_ex_calculator.py file
        stage_in.append(sd_shared_list[5])

        cu = radical.pilot.ComputeUnitDescription()
        cu.pre_exec = self.pre_exec
        cu.executable = "python"
        cu.input_staging  = stage_in
        cu.arguments = ["global_ex_calculator.py", str(cycle), str(self.replicas), str(self.inp_basename)]
        cu.cores = 1
        cu.mpi = False         
        cu.output_staging = stage_out

        return cu

    #---------------------------------------------------------------------------
    #
    def perform_swap(self, replica_i, replica_j):
        """Performs an exchange of temperatures

        Arguments:
        replica_i - a replica object
        replica_j - a replica object
        """

        rstr = replica_j.new_restraints
        replica_j.new_restraints = replica_i.new_restraints
        replica_i.new_restraints = rstr

        val = replica_j.rstr_val_1
        replica_j.rstr_val_1 = replica_i.rstr_val_1
        replica_i.rstr_val_1 = val
        # record that swap was performed
        replica_i.swap = 1
        replica_j.swap = 1

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

