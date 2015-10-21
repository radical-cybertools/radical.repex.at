"""
.. module:: radical.repex.md_kernles_tex.amber_kernels_tex.kernel_pattern_s_tex
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
import radical.utils.logger as rul
from kernels.kernels import KERNELS
import amber_kernels_tex.input_file_builder
#import amber_kernels_tex.global_ex_calculator_mpi
import amber_kernels_tex.global_ex_calculator
import amber_kernels_tex.ind_ex_calculator
from replicas.replica import *

#-------------------------------------------------------------------------------

class KernelPatternStex(object):
    
    def __init__(self, inp_file, rconfig,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as 
        specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        self.name = 'amber-tremd-patternA'
        self.ex_name = 'temperature'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        if 'number_of_cycles' in inp_file['remd.input']:
            self.nr_cycles = int(inp_file['remd.input']['number_of_cycles'])
        else:
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

        if 'replica_cores' in inp_file['remd.input']:
            self.replica_cores = int(inp_file['remd.input']['replica_cores'])
        else:
            self.replica_cores = 1

        self.resource = rconfig['target']['resource']
        self.cores    = int(rconfig['target']['cores'])
        self.pre_exec = KERNELS[self.resource]["kernels"]["amber"]["pre_execution"]

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

        if self.resource == 'local.localhost':
            if 'amber_path' in inp_file['remd.input']:
                self.amber_path = inp_file['remd.input']['amber_path']
            else:
                self.logger.info("Amber path for {0} is not defined".format( rconfig['target']['resource'] ) )
                sys.exit(1)
        else:
            if 'amber_path' in inp_file['remd.input']:
                self.amber_path = inp_file['remd.input']['amber_path']
            else:
                self.logger.info("Using default Amber path for: {0}".format( rconfig['target']['resource'] ) )
                try:
                    self.amber_path = KERNELS[self.resource]["kernels"]["amber"]["executable"]
                except:
                    self.logger.info("Amber path for {0} is not defined".format( rconfig['target']['resource'] ) )

        self.input_folder = inp_file['remd.input']['input_folder']   
        self.amber_coordinates = inp_file['remd.input']['amber_coordinates']
        self.amber_parameters = inp_file['remd.input']['amber_parameters']
        self.amber_input = inp_file['remd.input']['amber_input']
        self.input_folder = inp_file['remd.input']['input_folder']
        self.inp_basename = inp_file['remd.input']['input_file_basename']
        self.replicas = int(inp_file['remd.input']['number_of_replicas'])
        self.min_temp = float(inp_file['remd.input']['min_temperature'])
        self.max_temp = float(inp_file['remd.input']['max_temperature'])
        self.cycle_steps = int(inp_file['remd.input']['steps_per_cycle'])
        self.work_dir_local = work_dir_local

        self.current_cycle = -1
 
        self.shared_urls = []
        self.shared_files = []

        self.all_temp_list = []

    #---------------------------------------------------------------------------
    #
    def prepare_shared_data(self, replicas):
 
        parm_path = self.work_dir_local + "/" + self.input_folder + "/" + \
                    self.amber_parameters
        coor_path = self.work_dir_local + "/" + self.input_folder + "/" + \
                    self.amber_coordinates
                    
        input_template = self.inp_basename[:-5] + ".mdin"
        input_template_path = self.work_dir_local + "/" + self.input_folder + "/" + input_template

        build_inp = os.path.dirname(amber_kernels_tex.input_file_builder.__file__)
        build_inp_path = build_inp + "/input_file_builder.py"

        global_calc = os.path.dirname(amber_kernels_tex.global_ex_calculator.__file__)
        global_calc_path = global_calc + "/global_ex_calculator.py"

        global_calc_s = os.path.dirname(amber_kernels_tex.global_ex_calculator.__file__)
        global_calc_path_s = global_calc_s + "/global_ex_calculator.py"

        ind_calc = os.path.dirname(amber_kernels_tex.ind_ex_calculator.__file__)
        ind_calc_path = ind_calc + "/ind_ex_calculator.py"

        #-----------------------------------------------------------------------
        self.shared_files.append(self.amber_parameters)
        self.shared_files.append(self.amber_coordinates)
        self.shared_files.append(input_template)
        self.shared_files.append("input_file_builder.py")
        self.shared_files.append("global_ex_calculator.py")
        self.shared_files.append("global_ex_calculator.py")
        self.shared_files.append("ind_ex_calculator.py")

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

        global_calc_url_s = 'file://%s' % (global_calc_path_s)
        self.shared_urls.append(global_calc_url_s)

        ind_calc_url = 'file://%s' % (ind_calc_path)
        self.shared_urls.append(ind_calc_url)

    #---------------------------------------------------------------------------
    #
    def initialize_replicas(self):
        """Initializes replicas and their attributes to default values

           Changed to use geometrical progression for temperature assignment.
        """
        replicas = []
        N = self.replicas
        factor = (self.max_temp/self.min_temp)**(1./(N-1))
        for k in range(N):
            new_temp = self.min_temp * (factor**k)
            r = Replica1d(k, new_temperature=new_temp)
            replicas.append(r)
            
        return replicas

    #---------------------------------------------------------------------------
    #
    def prepare_replica_for_md(self, replica, sd_shared_list):

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
            #"new_restraints" : str(self.amber_restraints),
            "new_temperature" : str(replica.new_temperature),
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
           
        basename = self.inp_basename
        matrix_col = "matrix_column_%s_%s.dat" % (str(replica.id), str(replica.cycle-1))

        stage_out = []
        col_out = {
            'source': matrix_col,
            'target': 'staging:///%s' % matrix_col,
            'action': radical.pilot.COPY
        }
        stage_out.append(col_out)

        cu = radical.pilot.ComputeUnitDescription()
        cu.executable = "python"
        cu.input_staging  = sd_shared_list[6]
        cu.output_staging = stage_out
        cu.arguments = ["ind_ex_calculator.py", replica.id, (replica.cycle-1), self.replicas, basename, replica.new_temperature]
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

        # so that Ioannis can't use it!
        """
        if self.exchange_mpi == True:
            # global_ex_calculator_mpi.py file
            stage_in.append(sd_shared_list[4])

            cu = radical.pilot.ComputeUnitDescription()
            cu.pre_exec = self.pre_exec
            cu.executable = "python"
            cu.input_staging  = stage_in
            cu.arguments = ["global_ex_calculator_mpi.py", str(cycle), str(self.replicas), str(self.inp_basename)]

            # guard for supermic
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

        # swap temperatures
        temperature = replica_j.new_temperature
        replica_j.new_temperature = replica_i.new_temperature
        replica_i.new_temperature = temperature
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

