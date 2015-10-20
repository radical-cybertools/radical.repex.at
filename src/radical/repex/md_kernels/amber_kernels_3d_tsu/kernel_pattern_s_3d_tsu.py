"""
.. module:: radical.repex.md_kernles.amber_kernels_3d_tsu.kernel_pattern_s_3d_tsu
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
from kernels.kernels import KERNELS
from replicas.replica import Replica3d
import amber_kernels_3d_tsu.matrix_calculator_temp_ex
import amber_kernels_3d_tsu.matrix_calculator_us_ex
import amber_kernels_3d_tsu.input_file_builder
import amber_kernels_3d_tsu.salt_conc_pre_exec
import amber_kernels_3d_tsu.salt_conc_post_exec
import amber_kernels_3d_tsu.global_ex_calculator

#-------------------------------------------------------------------------------
#
class KernelPatternS3dTSU(object):
    """TODO
    """
    def __init__(self, inp_file, rconfig, work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as 
        specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        self.dims = 3

        self.resource = rconfig['target']['resource']

        self.amber_coordinates = inp_file['remd.input']['amber_coordinates']
        self.amber_parameters = inp_file['remd.input']['amber_parameters']

        if 'number_of_cycles' in inp_file['remd.input']:
            self.nr_cycles = int(inp_file['remd.input']['number_of_cycles'])
        else:
            self.nr_cycles = None
        
        self.input_folder = inp_file['remd.input']['input_folder']
        self.inp_basename = inp_file['remd.input']['input_file_basename']
        self.cycle_steps = int(inp_file['remd.input']['steps_per_cycle'])
        self.work_dir_local = work_dir_local
        self.amber_input = inp_file['remd.input']['amber_input']

        #-----------------------------------------------------------------------
        if 'exchange_off' in inp_file['remd.input']:
            if inp_file['remd.input']['exchange_off'] == "True":
                self.exchange_off = True
            else:
                self.exchange_off = False
        else:
            self.exchange_off = False
        #-----------------------------------------------------------------------

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

        if 'replica_mpi' in inp_file['remd.input']:
            if inp_file['remd.input']['replica_mpi'] == "True":
                self.md_replica_mpi = True
            else:
                self.md_replica_mpi = False
        else:
            self.md_replica_mpi= False

        if 'replica_cores' in inp_file['remd.input']:
            self.md_replica_cores = int(inp_file['remd.input']['replica_cores'])
        else:
            self.md_replica_cores = 1

        self.us_template = inp_file['remd.input']['us_template']                       
        self.current_cycle = -1

        # for now defaults to True in all cases!
        self.amber_coordinates_path = inp_file['remd.input']['amber_coordinates_folder']
        if 'same_coordinates' in inp_file['remd.input']:
            coors = inp_file['remd.input']['same_coordinates']
            if coors == "True":
                self.same_coordinates = True
            else:
                self.same_coordinates = True
        else:
            self.same_coordinates = True

        # hardcoded for now
        self.replicas_d1 = int(inp_file['dim.input']\
                           ['temperature_1']["number_of_replicas"])
        self.replicas_d2 = int(inp_file['dim.input']\
                           ['salt_concentration_2']["number_of_replicas"])
        self.replicas_d3 = int(inp_file['dim.input']\
                           ['umbrella_sampling_3']["number_of_replicas"])

        #-----------------------------------------------------------------------
        # hardcoding dimension names
        self.d1 = 'temperature'
        self.d2 = 'salt_concentration'
        self.d3 = 'umbrella_sampling'

        # temperature exchange
        self.min_temp = float(inp_file['dim.input']\
                        ['temperature_1']['min_temperature'])
        self.max_temp = float(inp_file['dim.input']\
                        ['temperature_1']['max_temperature'])

        self.temp_ex_cores = int(inp_file['dim.input']\
                             ['temperature_1']['exchange_replica_cores'])
        if 'exchange_replica_mpi' in inp_file['dim.input']['temperature_1']:
            if inp_file['dim.input']\
                ['temperature_1']['exchange_replica_mpi'] == 'True':
                self.temp_ex_mpi = True
            else:
                self.temp_ex_mpi = False

        # salt concentration
        self.min_salt = float(inp_file['dim.input']\
                        ['salt_concentration_2']['min_salt'])
        self.max_salt = float(inp_file['dim.input']\
                        ['salt_concentration_2']['max_salt'])

        self.salt_ex_cores = int(inp_file['dim.input']\
                             ['salt_concentration_2']['exchange_replica_cores'])
        if 'exchange_replica_mpi' in inp_file['dim.input']\
                                             ['salt_concentration_2']:
            if inp_file['dim.input']['salt_concentration_2']\
                                    ['exchange_replica_mpi'] == 'True':
                self.salt_ex_mpi = True
            else:
                self.salt_ex_mpi = False

        # umbrella sampling
        self.us_start_param = float(inp_file['dim.input']\
                              ['umbrella_sampling_3']['us_start_param'])
        self.us_end_param = float(inp_file['dim.input']\
                            ['umbrella_sampling_3']['us_end_param'])

        self.us_ex_cores = int(inp_file['dim.input']\
                           ['umbrella_sampling_3']['exchange_replica_cores'])
        if 'exchange_replica_mpi' in inp_file['dim.input']\
                                             ['umbrella_sampling_3']:
            if inp_file['dim.input']\
                ['umbrella_sampling_3']['exchange_replica_mpi'] == 'True':
                self.us_ex_mpi = True
            else:
                self.us_ex_mpi = False

        self.replicas = self.replicas_d1 * self.replicas_d2 * self.replicas_d3 
        self.restraints_files = []
        for k in range(self.replicas):
            self.restraints_files.append(self.us_template + "." + str(k) )

        #-----------------------------------------------------------------------

        self.name = 'ak-patternB-3d-TSU'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        self.pre_exec = KERNELS[self.resource]["kernels"]["amber"]["pre_execution"]
        try:
            self.amber_path = inp_file['remd.input']['amber_path']
        except:
            self.logger.info("Using default Amber path for: {0}".format(rconfig['target']['resource']) )
            try:
                self.amber_path = KERNELS[self.resource]["kernels"]["amber"]["executable"]
            except:
                self.logger.info("Amber path for localhost is not defined!")

        self.amber_path_mpi = KERNELS[self.resource]["kernels"]["amber"]["executable_mpi"]

        self.shared_urls = []
        self.shared_files = []

        self.all_temp_list = []
        self.all_salt_list = []
        self.all_rstr_list = []

        self.d1_id_matrix = []
        self.d2_id_matrix = []
        self.d3_id_matrix = []        

        self.temp_matrix = []
        self.salt_matrix = []
        self.us_matrix = []

    #---------------------------------------------------------------------------
    #
    def get_rstr_id(self, restraint):
        dot = 0
        rstr_id = ''
        for ch in restraint:
            if dot == 2:
                rstr_id += ch
            if ch == '.':
                dot += 1

        return int(rstr_id)

    #---------------------------------------------------------------------------
    # 
    def initialize_replicas(self):
        """Initializes replicas and their attributes to default values
        """

        #-----------------------------------------------------------------------
        # parse coor file
        coor_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_coordinates_path
        coor_list  = listdir(coor_path)

        base = coor_list[0]

        self.coor_basename = base.split('inpcrd')[0]+'inpcrd'

        replicas = []

        d1_params = []
        N = self.replicas_d1
        factor = (self.max_temp/self.min_temp)**(1./(N-1))
        for k in range(N):
            new_temp = self.min_temp * (factor**k)
            d1_params.append(new_temp)

        d2_params = []
        N = self.replicas_d2
        for k in range(N):
            new_salt = (self.max_salt-self.min_salt)/(N-1)*k + self.min_salt
            d2_params.append(new_salt)

        for i in range(self.replicas_d1):
            t1 = float(d1_params[i])
            for j in range(self.replicas_d2):
                s1 = float(d2_params[j])
                for k in range(self.replicas_d3):
                    #-----------------------------------------------------------

                    rid = k + j*self.replicas_d3 + i*self.replicas_d3*self.replicas_d2
                    r1 = self.restraints_files[rid]

                    spacing = (self.us_end_param - self.us_start_param) / float(self.replicas_d3)
                    starting_value = self.us_start_param + k*spacing
                    rstr_val_1 = str(starting_value+spacing)
                    
                    r = Replica3d(rid, new_temperature=t1, new_salt=s1, new_restraints=r1, rstr_val_1=float(rstr_val_1), cores=1)
                    replicas.append(r)

        return replicas
    # --------------------------------------------------------------------------
    #
    def prepare_shared_data(self, replicas):

        parm_path = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_parameters
        coor_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_coordinates
        inp_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_input

        calc_temp = os.path.dirname(amber_kernels_3d_tsu.matrix_calculator_temp_ex.__file__)
        calc_temp_path = calc_temp + "/matrix_calculator_temp_ex.py"

        calc_us_ex = os.path.dirname(amber_kernels_3d_tsu.matrix_calculator_us_ex.__file__)
        calc_us_ex_path = calc_us_ex + "/matrix_calculator_us_ex.py"
   
        salt_pre_exec  = os.path.dirname(amber_kernels_3d_tsu.salt_conc_pre_exec.__file__)
        salt_pre_exec_path = salt_pre_exec + "/salt_conc_pre_exec.py"

        salt_post_exec  = os.path.dirname(amber_kernels_3d_tsu.salt_conc_post_exec.__file__)
        salt_post_exec_path = salt_post_exec + "/salt_conc_post_exec.py"

        build_inp = os.path.dirname(amber_kernels_3d_tsu.input_file_builder.__file__)
        build_inp_path = build_inp + "/input_file_builder.py"

        global_calc = os.path.dirname(amber_kernels_3d_tsu.global_ex_calculator.__file__)
        global_calc_path = global_calc + "/global_ex_calculator.py"

        rstr_template_path = self.work_dir_local + "/" + self.input_folder + "/" + self.us_template

        #-----------------------------------------------------------------------

        self.shared_files.append(self.amber_parameters)
        self.shared_files.append(self.amber_coordinates)
        self.shared_files.append(self.amber_input)
        self.shared_files.append("matrix_calculator_temp_ex.py")
        self.shared_files.append("matrix_calculator_us_ex.py")
        self.shared_files.append("salt_conc_pre_exec.py")
        self.shared_files.append("salt_conc_post_exec.py")
        self.shared_files.append("input_file_builder.py")
        self.shared_files.append("global_ex_calculator.py")
        self.shared_files.append(self.us_template)
        #-----------------------------------------------------------------------

        parm_url = 'file://%s' % (parm_path)
        self.shared_urls.append(parm_url)

        coor_url = 'file://%s' % (coor_path)
        self.shared_urls.append(coor_url)

        inp_url = 'file://%s' % (inp_path)
        self.shared_urls.append(inp_url)

        calc_temp_url = 'file://%s' % (calc_temp_path)
        self.shared_urls.append(calc_temp_url)

        calc_us_ex_url = 'file://%s' % (calc_us_ex_path)
        self.shared_urls.append(calc_us_ex_url)

        salt_pre_exec_url = 'file://%s' % (salt_pre_exec_path)
        self.shared_urls.append(salt_pre_exec_url)

        salt_post_exec_url = 'file://%s' % (salt_post_exec_path)
        self.shared_urls.append(salt_post_exec_url)

        build_inp_url = 'file://%s' % (build_inp_path)
        self.shared_urls.append(build_inp_url)

        global_calc_url = 'file://%s' % (global_calc_path)
        self.shared_urls.append(global_calc_url)

        rstr_template_url = 'file://%s' % (rstr_template_path)
        self.shared_urls.append(rstr_template_url)
 
    #---------------------------------------------------------------------------
    #
    def prepare_replica_for_md(self, dimension, replicas, replica, sd_shared_list):
        """
        """

        basename = self.inp_basename

        new_input_file = "%s_%d_%d.mdin" % (basename, replica.id, replica.cycle)
        outputname = "%s_%d_%d.mdout" % (basename, replica.id, replica.cycle)
        old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1))

        # new files
        replica.new_coor = "%s_%d_%d.rst" % (basename, replica.id, replica.cycle)
        replica.new_traj = "%s_%d_%d.mdcrd" % (basename, replica.id, replica.cycle)
        replica.new_info = "%s_%d_%d.mdinfo" % (basename, replica.id, replica.cycle)

        # old files
        replica.old_coor = old_name + ".rst"
        replica.old_traj = old_name + ".mdcrd"
        replica.old_info = old_name + ".mdinfo"
        
        replica.cycle += 1
        #-----------------------------------------------------------------------
      
        crds = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_coordinates
        input_file = "%s_%d_%d.mdin" % (self.inp_basename, replica.id, (replica.cycle-1))
        output_file = "%s_%d_%d.mdout" % (self.inp_basename, replica.id, (replica.cycle-1))

        stage_out = []
        stage_in = []

        new_coor = replica.new_coor
        new_traj = replica.new_traj
        new_info = replica.new_info
        old_coor = replica.old_coor
        old_traj = replica.old_traj
        rid = replica.id

        replica_path = "replica_%d/" % (rid)
        #-----------------------------------------------------------------------

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

        out_string = "_%d.out" % (replica.cycle-1)
        rstr_out = {
            'source': (replica.new_restraints + '.out'),
            'target': 'staging:///%s' % (replica_path + replica.new_restraints + out_string),
            'action': radical.pilot.COPY
        }
        stage_out.append(rstr_out)
        
        #-----------------------------------------------------------------------
        # common code from prepare_for_exchange()
        
        matrix_col = "matrix_column_%s_%s.dat" % (str(replica.id), str(replica.cycle-1))

        # for all cases!
        matrix_col_out = {
            'source': matrix_col,
            'target': 'staging:///%s' % (matrix_col),
            'action': radical.pilot.COPY
        }
        stage_out.append(matrix_col_out)

        # for all cases (OPTIONAL)    
        info_out = {
                'source': new_info,
                'target': 'staging:///%s' % (replica_path + new_info),
                'action': radical.pilot.COPY
            }
        stage_out.append(info_out)

        current_group = self.get_current_group(dimension, replicas, replica)
        #-----------------------------------------------------------------------
        # json for input_file_builder.py
        data = {
            "cycle_steps": str(self.cycle_steps),
            "new_restraints" : str(replica.new_restraints),
            "new_temperature" : str(replica.new_temperature),
            "new_salt_concentration" : str(replica.new_salt_concentration),
            "amber_input" : str(self.amber_input),
            "new_input_file" : str(new_input_file),
            "us_template": str(self.us_template),
            "cycle" : str(replica.cycle),
            "rstr_val_1" : str(replica.rstr_val_1),
            "rid" : str(rid)
                }
        dump_data = json.dumps(data)
        json_pre_data_bash = dump_data.replace("\\", "")
        json_pre_data_sh   = dump_data.replace("\"", "\\\\\"")

        #-----------------------------------------------------------------------
        # json for matrix_calculator_temp_ex.py
        data = {
            "replica_id": str(replica.id),
            "replica_cycle" : str(replica.cycle-1),
            "base_name" : str(basename),
            "current_group" : current_group,
            "replicas" : str(len(replicas)),
            "amber_parameters": str(self.amber_parameters),
            "new_restraints" : str(replica.new_restraints),
            "init_temp" : str(replica.new_temperature),
            "init_salt" : str(replica.new_salt_concentration)
            }

        dump_data = json.dumps(data)
        json_post_data_temp_bash = dump_data.replace("\\", "")
        json_post_data_temp_sh   = dump_data.replace("\"", "\\\\\"")

        #-----------------------------------------------------------------------
        # json for matrix_calculator_us_ex.py

        current_group_rst = {}
        for repl in replicas:
            if str(repl.id) in current_group:
                current_group_rst[str(repl.id)] = str(repl.new_restraints)

        base_restraint = self.us_template + "."

        data = {
            "replica_id": str(rid),
            "replica_cycle" : str(replica.cycle-1),
            "replicas" : str(self.replicas),
            "base_name" : str(basename),
            "init_temp" : str(replica.new_temperature),
            "init_salt" : str(replica.new_salt_concentration),
            "amber_input" : str(self.amber_input),
            "amber_parameters": str(self.amber_parameters),
            "new_restraints" : str(replica.new_restraints),
            "current_group_rst" : current_group_rst
        }
        dump_data = json.dumps(data)
        json_post_data_us_bash = dump_data.replace("\\", "")
        json_post_data_us_sh   = dump_data.replace("\"", "\\\\\"")

        #-----------------------------------------------------------------------
        # json for matrix_calculator_salt_ex.py

        current_group_tsu = {}
        for repl in replicas:
            if str(repl.id) in current_group:
                current_group_tsu[str(repl.id)] = [str(repl.new_temperature), \
                                                   str(repl.new_salt_concentration), \
                                                   str(repl.new_restraints)]

        data = {
            "replica_id": str(replica.id),
            "replica_cycle" : str(replica.cycle-1),
            "replicas" : str(self.replicas),
            "base_name" : str(basename),
            "init_temp" : str(replica.new_temperature),
            "amber_path" : str(self.amber_path),
            "amber_input" : str(self.amber_input),
            "amber_parameters": "../staging_area/"+str(self.amber_parameters),    
            "current_group_tsu" : current_group_tsu, 
            "r_old_path": str(replica.old_path),
        }

        dump_data = json.dumps(data)
        json_data_salt_bash = dump_data.replace("\\", "")
        json_data_salt_sh   = dump_data.replace("\"", "\\\\\"")

        #-----------------------------------------------------------------------

        cu = radical.pilot.ComputeUnitDescription()
        if KERNELS[self.resource]["shell"] == "bash":
            cu.executable = '/bin/bash'
            pre_exec_str = "python input_file_builder.py " + "\'" + json_pre_data_bash + "\'" 
            post_exec_str_temp = "python matrix_calculator_temp_ex.py " + "\'" + json_post_data_temp_bash + "\'"
            post_exec_str_us = "python matrix_calculator_us_ex.py " + "\'" + json_post_data_us_bash + "\'"
            pre_exec_str_salt = "python salt_conc_pre_exec.py " + "\'" + json_data_salt_bash + "\'"
            post_exec_str_salt = "python salt_conc_post_exec.py " + "\'" + json_data_salt_bash + "\'"
        elif KERNELS[self.resource]["shell"] == "bourne":
            cu.executable = '/bin/sh'
            pre_exec_str = "python input_file_builder.py " + "\'" + json_pre_data_sh + "\'" 
            post_exec_str_temp = "python matrix_calculator_temp_ex.py " + "\'" + json_post_data_temp_sh + "\'"
            post_exec_str_us = "python matrix_calculator_us_ex.py " + "\'" + json_post_data_us_sh + "\'"
            pre_exec_str_salt = "python salt_conc_pre_exec.py " + "\'" + json_data_salt_sh + "\'"
            post_exec_str_salt = "python salt_conc_post_exec.py " + "\'" + json_data_salt_sh + "\'"
        #-----------------------------------------------------------------------

        if replica.cycle == 1:

            amber_str = self.amber_path
            argument_str = " -O " + " -i " + new_input_file + \
                           " -o " + output_file + \
                           " -p " +  self.amber_parameters + \
                           " -c " + self.amber_coordinates + \
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
            # files needed to be staged in replica dir (params, coors, amber_input)
            for i in range(3):
                stage_in.append(sd_shared_list[i])

            # input_file_builder.py
            stage_in.append(sd_shared_list[7])

            # restraint template file: ace_ala_nme_us.RST
            stage_in.append(sd_shared_list[9])

            #-------------------------------------------------------------------
            # temperature exchange
            if dimension == 1:
                # copying matrix_calculator_temp_ex.py from staging area to cu folder
                stage_in.append(sd_shared_list[3])
                
                cu.arguments = ['-c', pre_exec_str + "; " + amber_str + argument_str + "; " + post_exec_str_temp] 
                cu.pre_exec = self.pre_exec
                cu.cores = self.md_replica_cores
                cu.input_staging = stage_in
                cu.output_staging = stage_out
                cu.mpi = self.md_replica_mpi
            
        #-----------------------------------------------------------------------
        # from cycle 2 onwards   
        else:

            amber_str = self.amber_path
            argument_str = " -O " + " -i " + new_input_file + \
                           " -o " + output_file + \
                           " -p " +  self.amber_parameters + \
                           " -c " + old_coor + \
                           " -r " + new_coor + \
                           " -x " + new_traj + \
                           " -inf " + new_info

            # parameters file
            stage_in.append(sd_shared_list[0])

            # base input file ala10_us.mdin
            stage_in.append(sd_shared_list[2])

            # input_file_builder.py
            stage_in.append(sd_shared_list[7])
            #-------------------------------------------------------------------
            # restraint file
            restraints_in_st = {'source': 'staging:///%s' % replica.new_restraints,
                                'target': replica.new_restraints,
                                'action': radical.pilot.COPY
            }
            stage_in.append(restraints_in_st)

            old_coor_st = {'source': 'staging:///%s' % (replica_path + old_coor),
                           'target': (old_coor),
                           'action': radical.pilot.LINK
            }
            stage_in.append(old_coor_st)

            if dimension == 1:
                #---------------------------------------------------------------
                # matrix_calculator_temp_ex.py file
                stage_in.append(sd_shared_list[3])
               
                cu.arguments = ['-c', pre_exec_str + "; " + amber_str + argument_str + "; " + post_exec_str_temp] 
                cu.pre_exec = self.pre_exec
                cu.input_staging = stage_in
                cu.output_staging = stage_out
                cu.cores = self.md_replica_cores
                cu.mpi = self.md_replica_mpi
            elif dimension == 2:
                # salt concentration

                # copying amber_input from staging area to cu folder
                stage_in.append(sd_shared_list[2])
                      
                cu.arguments = ['-c', pre_exec_str + "; " + amber_str + argument_str]   
                cu.cores = self.md_replica_cores
                cu.pre_exec = self.pre_exec     
                cu.mpi = self.md_replica_mpi
                cu.output_staging = stage_out 
                cu.input_staging = stage_in
            else:
                # us exchange

                # copying calculator from staging area to cu folder
                stage_in.append(sd_shared_list[4])                
                
                cu.arguments = ['-c', pre_exec_str + "; " + amber_str + argument_str + "; " + post_exec_str_us] 
                cu.pre_exec = self.pre_exec
                cu.input_staging = stage_in
                cu.output_staging = stage_out
                cu.cores = self.md_replica_cores
                cu.mpi = self.md_replica_mpi           

        return cu

    #---------------------------------------------------------------------------
    #
    def prepare_lists(self, replicas):

        pass

    #---------------------------------------------------------------------------
    #
    def prepare_replica_for_exchange(self, dimension, replicas, replica, sd_shared_list):
        """
        """
        # name of the file which contains swap matrix column data for each replica
        basename = self.inp_basename
        matrix_col = "matrix_column_%s_%s.dat" % (str(replica.id), str(replica.cycle-1))

        current_group = self.get_current_group(dimension, replicas, replica)

        #print "current group for replica: {0}".format(replica.id)
        #print current_group

        cu = radical.pilot.ComputeUnitDescription()
        
        if dimension == 2:
            # 
            current_group_tsu = {}
            for repl in replicas:
                if str(repl.id) in current_group:
                    current_group_tsu[str(repl.id)] = [str(repl.new_temperature), \
                                                       str(repl.new_salt_concentration), \
                                                       str(repl.new_restraints)]

            data = {
                "replica_id": str(replica.id),
                "replica_cycle" : str(replica.cycle-1),
                "replicas" : str(self.replicas),
                "base_name" : str(basename),
                "init_temp" : str(replica.new_temperature),
                "init_salt" : str(replica.new_salt_concentration),
                "new_restraints" : str(replica.new_restraints),
                "amber_path" : str(self.amber_path),
                "amber_input" : str(self.amber_input),
                "amber_parameters": str(self.amber_parameters), 
                "current_group_tsu" : current_group_tsu, 
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

            # copying .RST files from staging area to replica folder
            rst_group = []
            for k in current_group_tsu.keys():
                rstr_id = self.get_rstr_id(current_group_tsu[k][2])
                rst_group.append(rstr_id)

            for rsid in rst_group:
                rst_file = self.us_template + '.' + str(rsid)
                rstr_in = {
                    'source': 'staging:///%s' % (rst_file),
                    'target': rst_file,
                    'action': radical.pilot.COPY
                }
                in_list.append(rstr_in)
      
            cu.input_staging = in_list

            out_list = []
            matrix_col_out = {
                'source': matrix_col,
                'target': 'staging:///%s' % (matrix_col),
                'action': radical.pilot.COPY
            }
            out_list.append(matrix_col_out)

            cu.arguments = ['-ng', str(self.replicas_d2), '-groupfile', 'groupfile']
            cu.cores = self.replicas_d2
            cu.mpi = self.salt_ex_mpi
            cu.output_staging = out_list   

        return cu

    #---------------------------------------------------------------------------
    #
    def exchange_params(self, dimension, replica_1, replica_2):
        
        if dimension == 1:
            self.logger.info("[exchange_params] before: r1: {0} r2: {1}"\
                .format(replica_1.new_temperature, replica_2.new_temperature) )
            temp = replica_2.new_temperature
            replica_2.new_temperature = replica_1.new_temperature
            replica_1.new_temperature = temp
            self.logger.info("[exchange_params] after: r1: {0} r2: {1}"\
                .format(replica_1.new_temperature, replica_2.new_temperature) )
        elif dimension == 2:
            self.logger.info("[exchange_params] before: r1: {0:0.2f} \
                r2: {1:0.2f}".format(replica_1.new_salt_concentration, \
                                     replica_2.new_salt_concentration) )
            salt = replica_2.new_salt_concentration
            replica_2.new_salt_concentration = replica_1.new_salt_concentration
            replica_1.new_salt_concentration = salt
            self.logger.info("[exchange_params] after: r1: {0:0.2f} \
                r2: {1:0.2f}".format(replica_1.new_salt_concentration, \
                                     replica_2.new_salt_concentration) )
        else:
            self.logger.info("[exchange_params] before: r1: {0} \
                r2: {1}".format(replica_1.new_restraints, \
                                     replica_2.new_restraints) )

            rstr = replica_2.new_restraints
            replica_2.new_restraints = replica_1.new_restraints
            replica_1.new_restraints = rstr

            val = replica_2.rstr_val_1
            replica_2.rstr_val_1 = replica_1.rstr_val_1
            replica_1.rstr_val_1 = val

            self.logger.info("[exchange_params] after: r1: {0} \
                r2: {1}".format(replica_1.new_restraints, \
                                     replica_2.new_restraints) )

    #---------------------------------------------------------------------------
    #
    def do_exchange(self, current_cycle, dimension, replicas):
        """tuu
        """

        r1 = None
        r2 = None

        cycle = replicas[0].cycle-1

        infile = "pairs_for_exchange_{dim}_{cycle}.dat".format(dim=dimension, \
                                                               cycle=cycle)
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
                    print "r1 is None"
                    if r2 == None:
                        print "r2 is None"
                        rid = random.randint(0,(len(replicas)-1))
                        r1 = r2 = replicas[rid]
                    else:
                        r1 = r2
                #---------------------------------------------------------------

                # swap parameters
                if self.exchange_off == False:
                    self.exchange_params(dimension, r1, r2)
                    r1.swap = 1
                    r2.swap = 1
        except:
            raise

    #---------------------------------------------------------------------------
    #
    def init_matrices(self, replicas):
        """
        change...
        """

        # id_matrix
        for r in replicas:
            row = []
            row.append(r.id)
            for c in range(self.nr_cycles):
                row.append( -1.0 )

            self.d1_id_matrix.append( row )
            self.d2_id_matrix.append( row )
            self.d3_id_matrix.append( row )

        self.d1_id_matrix = sorted(self.d1_id_matrix)
        self.d2_id_matrix = sorted(self.d2_id_matrix)
        self.d3_id_matrix = sorted(self.d3_id_matrix)

        self.logger.debug("[init_matrices] d1_id_matrix: {0:s}"\
            .format(self.d1_id_matrix) )
        self.logger.debug("[init_matrices] d2_id_matrix: {0:s}"\
            .format(self.d2_id_matrix) )
        self.logger.debug("[init_matrices] d3_id_matrix: {0:s}"\
            .format(self.d3_id_matrix) )

        # temp_matrix
        for r in replicas:
            row = []
            row.append(r.id)
            row.append(r.new_temperature)
            for c in range(self.nr_cycles - 1):
                row.append( -1.0 )

            self.temp_matrix.append( row )

        self.temp_matrix = sorted(self.temp_matrix)
        self.logger.debug("[init_matrices] temp_matrix: {0:s}"\
            .format(self.temp_matrix) )

        # salt_matrix
        for r in replicas:
            row = []
            row.append(r.id)
            row.append(r.new_salt_concentration)
            for c in range(self.nr_cycles - 1):
                row.append( -1.0 )
            self.salt_matrix.append( row )

        self.salt_matrix = sorted(self.salt_matrix)
        self.logger.debug("[init_matrices] salt_matrix: {0:s}"\
            .format(self.salt_matrix) )

        # us_matrix
        for r in replicas:
            row = []
            row.append(r.id)
            row.append(r.rstr_val_1)
            for c in range(self.nr_cycles - 1):
                row.append( -1.0 )
            self.us_matrix.append( row )

        self.us_matrix = sorted(self.us_matrix)
        self.logger.debug("[init_matrices] us_d1_matrix: {0:s}"\
            .format(self.us_matrix) )

    #---------------------------------------------------------------------------
    #
    def get_current_group(self, dimension, replicas, replica):
        """
        """

        current_group = []

        for r1 in replicas:
            
            #-------------------------------------------------------------------
            # temperature exchange
            if dimension == 1:
                
                r1_pair = [r1.new_salt_concentration, r1.rstr_val_1]
                my_pair = [replica.new_salt_concentration, replica.rstr_val_1]
                  
                if r1_pair == my_pair:
                    current_group.append(str(r1.id))

            #-------------------------------------------------------------------
            # salt concentration exchange
            elif dimension == 2:

                r1_pair = [r1.new_temperature, r1.rstr_val_1]
                my_pair = [replica.new_temperature, replica.rstr_val_1]

                if r1_pair == my_pair:
                    current_group.append(str(r1.id))

            #-------------------------------------------------------------------
            # us exchange 
            elif dimension == 3:

                r1_pair = [r1.new_temperature, r1.new_salt_concentration]
                my_pair = [replica.new_temperature, \
                           replica.new_salt_concentration]

                if r1_pair == my_pair:
                    current_group.append(str(r1.id))

        # 
        if len(current_group) != self.replicas_d2:
            print "group has wrong size: {0}".format(len(current_group))
            
        return current_group

    #---------------------------------------------------------------------------
    #
    def prepare_global_ex_calc(self, GL, current_cycle, dimension, replicas, sd_shared_list):

        stage_out = []
        stage_in = []

        if GL == 1:
            cycle = replicas[0].cycle-1
        else:
            cycle = replicas[0].cycle
        
        # global_ex_calculator.py file
        stage_in.append(sd_shared_list[8])

        outfile = "pairs_for_exchange_{dim}_{cycle}.dat".format(dim=dimension, cycle=cycle)
        stage_out.append(outfile)

        cu = radical.pilot.ComputeUnitDescription()
        cu.pre_exec = self.pre_exec
        cu.executable = "python"
        cu.input_staging  = stage_in
        cu.arguments = ["global_ex_calculator.py", str(self.replicas), str(cycle), str(dimension)]
        cu.cores = 1
        cu.mpi = False            
        cu.output_staging = stage_out

        return cu
