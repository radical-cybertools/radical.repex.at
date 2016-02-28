"""
.. module:: radical.repex.md_kernles.amber_kernels_3d_tuu.kernel_pattern_s_3d_tuu
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
import tarfile
import datetime
from os import path
import radical.pilot
from os import listdir
from os.path import isfile, join
import radical.utils.logger as rul
from kernels.kernels import KERNELS
import amber_kernels_3d_tuu.remote_calculator_temp_ex_mpi
import amber_kernels_3d_tuu.remote_calculator_us_ex_mpi
import amber_kernels_3d_tuu.matrix_calculator_temp_ex
import amber_kernels_3d_tuu.matrix_calculator_us_ex
import amber_kernels_3d_tuu.input_file_builder
import amber_kernels_3d_tuu.global_ex_calculator_gr
import amber_kernels_3d_tuu.global_ex_calculator
import amber_kernels_3d_tuu.salt_conc_pre_exec
import amber_kernels_3d_tuu.salt_conc_post_exec
from replicas.replica import Replica3d

#-------------------------------------------------------------------------------
#
class KernelPatternS3D(object):
    """TODO
    """
    def __init__(self, inp_file, rconfig, work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as 
        specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        self.name = 'amber-pattern-s-3d'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        self.resource         = rconfig['target'].get('resource')
        self.inp_basename     = inp_file['remd.input'].get('input_file_basename')
        self.input_folder     = inp_file['remd.input'].get('input_folder')
        self.us_template      = inp_file['remd.input'].get('us_template', '') 
        self.amber_parameters = inp_file['remd.input'].get('amber_parameters')
        self.amber_input      = inp_file['remd.input'].get('amber_input')
        self.work_dir_local   = work_dir_local
        self.current_cycle    = -1

        self.cores         = int(rconfig['target'].get('cores', '1'))
        self.cycle_steps   = int(inp_file['remd.input'].get('steps_per_cycle'))
        self.nr_cycles     = int(inp_file['remd.input'].get('number_of_cycles','1'))
        self.replica_cores = int(inp_file['remd.input'].get('replica_cores', '1'))

        self.group_exec = inp_file['remd.input'].get('group_exec', 'False')
        if self.group_exec == 'True':
            self.group_exec = True
        else:
            self.group_exec = False

        if inp_file['remd.input'].get('replica_gpu') == "True":
            self.replica_gpu = True
        else:
            self.replica_gpu = False

        #-----------------------------------------------------------------------
    
        self.amber_coordinates_path = inp_file['remd.input'].get('amber_coordinates_folder')
        if inp_file['remd.input'].get('same_coordinates') == "True":
            self.same_coordinates = True
        else:
            self.same_coordinates = False

        if inp_file['remd.input'].get('download_mdinfo') == 'True':
            self.down_mdinfo = True
        else:
            self.down_mdinfo = False
     
        if inp_file['remd.input'].get('download_mdout') == 'True':
            self.down_mdout = True
        else:
            self.down_mdout = False

        if inp_file['remd.input'].get('replica_mpi') == "True":
            self.replica_mpi = True
        else:
            self.replica_mpi = False  

        if inp_file['remd.input'].get('exchange_off') == "True":
            self.exchange_off = True
        else:
            self.exchange_off = False  
    
        self.dims = {}
        self.dims['d1'] = {'replicas' : None, 'type' : None} 
        self.dims['d2'] = {'replicas' : None, 'type' : None}
        self.dims['d3'] = {'replicas' : None, 'type' : None}

        #-----------------------------------------------------------------------
        #  
        if inp_file['dim.input'].get('d1'):
            self.dims['d1']['replicas'] = int(inp_file['dim.input']\
                               ['d1'].get("number_of_replicas"))
            self.dims['d1']['type'] = (inp_file['dim.input']['d1'].get("type"))

        if inp_file['dim.input'].get('d2'):
            self.dims['d2']['replicas'] = int(inp_file['dim.input']\
                               ['d2'].get("number_of_replicas"))
            self.dims['d2']['type'] = (inp_file['dim.input']['d2'].get("type"))

        if inp_file['dim.input'].get('d3'):
            self.dims['d3']['replicas'] = int(inp_file['dim.input']\
                               ['d3'].get("number_of_replicas"))
            self.dims['d3']['type'] = (inp_file['dim.input']['d3'].get("type"))

        self.nr_dims = 0
        if self.dims['d1']['replicas'] and (not self.dims['d2']['replicas']) and (not self.dims['d3']['replicas']):
            self.nr_dims = 1
        if self.dims['d1']['replicas'] and self.dims['d2']['replicas'] and (not self.dims['d3']['replicas']):
            self.nr_dims = 2
        if self.dims['d1']['replicas'] and self.dims['d2']['replicas'] and self.dims['d3']['replicas']:
            self.nr_dims = 3

        if self.nr_dims == 0:
            self.logger.info("Number of dimensions must be greater than 0, exiting...")
            sys.exit(1)

        if self.nr_dims == 1:
            self.replicas = self.dims['d1']['replicas']
            self.ex_accept_id_matrix_d1 = []
        elif self.nr_dims == 2:
            self.replicas = self.dims['d1']['replicas'] * self.dims['d2']['replicas']
            self.ex_accept_id_matrix_d1 = []
            self.ex_accept_id_matrix_d2 = []
        elif self.nr_dims == 3:
            self.replicas = self.dims['d1']['replicas'] * self.dims['d2']['replicas'] * self.dims['d3']['replicas']
            self.ex_accept_id_matrix_d1 = []
            self.ex_accept_id_matrix_d2 = []
            self.ex_accept_id_matrix_d3 = []   

        self.restraints_files = []
        for k in range(self.replicas):
            self.restraints_files.append(self.us_template + "." + str(k) )
 
        for k in self.dims:
            if self.dims[k]['type'] == 'umbrella':
                self.dims[k]['us_start'] = float(inp_file['dim.input'][k].get('us_start_param'))
                self.dims[k]['us_end'] = float(inp_file['dim.input'][k].get('us_end_param'))
            if self.dims[k]['type'] == 'temperature':
                self.dims[k]['temp_start'] = float(inp_file['dim.input'][k].get('min_temperature'))
                self.dims[k]['temp_end'] = float(inp_file['dim.input'][k].get('max_temperature'))
            if self.dims[k]['type'] == 'salt':
                self.dims[k]['salt_start'] = float(inp_file['dim.input'][k].get('min_salt'))
                self.dims[k]['salt_end'] = float(inp_file['dim.input'][k].get('max_salt'))

        #-----------------------------------------------------------------------

        self.pre_exec = KERNELS[self.resource]["kernels"]\
                        ["amber"].get("pre_execution")

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

        self.shared_urls = []
        self.shared_files = []     

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
        
        #-----------------------------------------------------------------------
        # parse coor file
        coor_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_coordinates_path
        coor_list  = listdir(coor_path)
        base = coor_list[0]
        self.coor_basename = base.split('inpcrd')[0]+'inpcrd'

        #-----------------------------------------------------------------------
        replicas = []

        dim_params = {}
        for k in self.dims:
            N = self.dims[k]['replicas']
            dim_params[k] = []
            if self.dims[k]['type'] == 'temperature':
                factor = (self.dims[k]['temp_end']/self.dims[k]['temp_start'])**(1./(N-1))
                for i in range(N):
                    new_temp = self.dims[k]['temp_start'] * (factor**i)
                    dim_params[k].append(new_temp)
            if self.dims[k]['type'] == 'umbrella':
                for i in range(N):
                    spacing = (self.dims[k]['us_end'] - self.dims[k]['us_start']) / (float(self.dims[k]['replicas'])-1)
                    starting_value = self.dims[k]['us_start'] + i*spacing
                    dim_params[k].append(starting_value)
            if self.dims[k]['type'] == 'salt':
                for i in range(N):
                    new_salt = (self.dims[k]['salt_end']-self.dims[k]['salt_start'])/(N-1.0)*float(i) + self.dims[k]['salt_start']
                    dim_params[k].append(new_salt)

        if self.nr_dims == 3:
            for i in range(self.dims['d1']['replicas']):
                for j in range(self.dims['d2']['replicas']):
                    for k in range(self.dims['d3']['replicas']):
                        rid = k + j*self.dims['d3']['replicas'] + i*self.dims['d3']['replicas']*self.dims['d2']['replicas']

                        r = self.restraints_files[rid]
                        if self.same_coordinates == False:
                            indexes = []
                            if self.dims['d1']['type'] == 'umbrella':
                                indexes.append(i)
                            if self.dims['d2']['type'] == 'umbrella':
                                indexes.append(j)
                            if self.dims['d3']['type'] == 'umbrella':
                                indexes.append(k)
                            coor_file = self.coor_basename
                            for ind in indexes:
                                coor_file += "." + str(ind)
                        else:
                            coor_file = self.coor_basename + ".0.0.0"

                        r = Replica3d(rid, \
                                      new_restraints=r, \
                                      cores=1, \
                                      coor=coor_file,
                                      d1_param=float(dim_params['d1'][i]), \
                                      d2_param=float(dim_params['d2'][j]), \
                                      d3_param=float(dim_params['d3'][k]), \
                                      d1_type = self.dims['d1']['type'], \
                                      d2_type = self.dims['d2']['type'], \
                                      d3_type = self.dims['d3']['type'])
                        replicas.append(r)

        if self.nr_dims == 2:
            for i in range(self.dims['d1']['replicas']):
                for j in range(self.dims['d2']['replicas']):
                    rid = j + i*self.dims['d2']['replicas']

                    r = self.restraints_files[rid]
                    if self.same_coordinates == False:
                        indexes = []
                        if self.dims['d1']['type'] == 'umbrella':
                            indexes.append(i)
                        if self.dims['d2']['type'] == 'umbrella':
                            indexes.append(j)
                        coor_file = self.coor_basename
                        for ind in indexes:
                            coor_file += "." + str(ind)
                    else:
                        coor_file = self.coor_basename + ".0.0"

                    r = Replica2d(rid, \
                                  new_restraints=r, \
                                  cores=1, \
                                  coor=coor_file,
                                  d1_param=float(dim_params['d1'][i]), \
                                  d2_param=float(dim_params['d2'][j]), \
                                  d1_type = self.dims['d1']['type'], \
                                  d2_type = self.dims['d2']['type'], )
                    replicas.append(r)

        if self.nr_dims == 1:
            for i in range(self.dims['d1']['replicas']):
                rid = i

                r = self.restraints_files[rid]
                if self.same_coordinates == False:
                    coor_file = self.coor_basename
                    if self.dims['d1']['type'] == 'umbrella':
                        coor_file += "." + str(i)
                else:
                    coor_file = self.coor_basename + ".0"

                r = Replica1d(rid, \
                              new_restraints=r, \
                              cores=1, \
                              coor=coor_file,
                              d1_param=float(dim_params['d1'][i]), \
                              d1_type = self.dims['d1']['type'] )
                replicas.append(r)

        #-----------------------------------------------------------------------
        # assigning group idx

        if self.nr_dims == 3:
            g_d1 = []
            g_d2 = []
            g_d3 = []
            for r in replicas:
                if len(g_d1) == 0:
                    g_d1.append([r.dims['d2']['par'], r.dims['d3']['par']]) 
                    g_d2.append([r.dims['d1']['par'], r.dims['d3']['par']]) 
                    g_d3.append([r.dims['d1']['par'], r.dims['d2']['par']])
                for i in range(len(g_d1)):
                    if (g_d1[i][0] == r.dims['d2']['par']) and (g_d1[i][1] == r.dims['d3']['par']):
                        r.group_idx[0] = i
                if r.group_idx[0] == None:
                    g_d1.append([r.dims['d2']['par'], r.dims['d3']['par']])
                    r.group_idx[0] = len(g_d1) - 1
                        
                for i in range(len(g_d2)):
                    if (g_d2[i][0] == r.dims['d1']['par']) and (g_d2[i][1] == r.dims['d3']['par']):
                        r.group_idx[1] = i
                if r.group_idx[1] == None:
                    g_d2.append([r.dims['d1']['par'], r.dims['d3']['par']])
                    r.group_idx[1] = len(g_d2) - 1

                for i in range(len(g_d3)):
                    if (g_d3[i][0] == r.dims['d1']['par']) and (g_d3[i][1] == r.dims['d2']['par']):
                        r.group_idx[2] = i
                if r.group_idx[2] == None:
                    g_d3.append([r.dims['d1']['par'], r.dims['d2']['par']])
                    r.group_idx[2] = len(g_d3) - 1
            self.groups_numbers = [len(g_d1), len(g_d2), len(g_d3)] 

        if self.nr_dims == 2:
            g_d1 = []
            g_d2 = []

            for r in replicas:
                if len(g_d1) == 0:
                    g_d1.append(r.dims['d2']['par']) 
                    g_d2.append(r.dims['d1']['par']) 
                for i in range(len(g_d1)):
                    if (g_d1[i] == r.dims['d2']['par']):
                        r.group_idx[0] = i
                if r.group_idx[0] == None:
                    g_d1.append(r.dims['d2']['par'])
                    r.group_idx[0] = len(g_d1) - 1
                        
                for i in range(len(g_d2)):
                    if (g_d2[i] == r.dims['d1']['par']):
                        r.group_idx[1] = i
                if r.group_idx[1] == None:
                    g_d2.append(r.dims['d1']['par'])
                    r.group_idx[1] = len(g_d2) - 1

            self.groups_numbers = [len(g_d1), len(g_d2)] 
 
        self.salt_str = ''
        self.temperature_str = ''
        for d_str in self.dims:
            if self.dims[d_str]['type'] == 'temperature':
                self.temperature_str = d_str
            if self.dims[d_str]['type'] == 'salt':
                self.salt_str = d_str

        return replicas

    #---------------------------------------------------------------------------
    #
    def prepare_shared_data(self, replicas):

        coor_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_coordinates_path
        parm_path = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_parameters
        inp_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_input

        #-----------------------------------------------------------------------
        # for group exec only, check
        calc_temp_ex = os.path.dirname(amber_kernels_3d_tuu.remote_calculator_temp_ex_mpi.__file__)
        calc_temp_ex_path_gr = calc_temp_ex + "/remote_calculator_temp_ex_mpi.py"

        calc_us_ex = os.path.dirname(amber_kernels_3d_tuu.remote_calculator_us_ex_mpi.__file__)
        calc_us_ex_path_gr = calc_us_ex + "/remote_calculator_us_ex_mpi.py"

        global_calc = os.path.dirname(amber_kernels_3d_tuu.global_ex_calculator_gr.__file__)
        global_calc_path_gr = global_calc + "/global_ex_calculator_gr.py"
        #
        #-----------------------------------------------------------------------

        calc_temp_ex = os.path.dirname(amber_kernels_3d_tuu.matrix_calculator_temp_ex.__file__)
        calc_temp_ex_path = calc_temp_ex + "/matrix_calculator_temp_ex.py"

        calc_us_ex = os.path.dirname(amber_kernels_3d_tuu.matrix_calculator_us_ex.__file__)
        calc_us_ex_path = calc_us_ex + "/matrix_calculator_us_ex.py"

        global_calc = os.path.dirname(amber_kernels_3d_tuu.global_ex_calculator.__file__)
        global_calc_path = global_calc + "/global_ex_calculator.py"

        rstr_template_path = self.work_dir_local + "/" + self.input_folder + "/" + self.us_template

        build_inp = os.path.dirname(amber_kernels_3d_tuu.input_file_builder.__file__)
        build_inp_path = build_inp + "/input_file_builder.py"

        salt_pre_exec  = os.path.dirname(amber_kernels_3d_tuu.salt_conc_pre_exec.__file__)
        salt_pre_exec_path = salt_pre_exec + "/salt_conc_pre_exec.py"

        salt_post_exec  = os.path.dirname(amber_kernels_3d_tuu.salt_conc_post_exec.__file__)
        salt_post_exec_path = salt_post_exec + "/salt_conc_post_exec.py"

        #-----------------------------------------------------------------------
        # now adding to shared_files:

        self.shared_files.append(self.amber_parameters)
        self.shared_files.append(self.amber_input)

        if self.group_exec == True:
            self.shared_files.append("remote_calculator_temp_ex_mpi.py")
            self.shared_files.append("remote_calculator_us_ex_mpi.py")
            self.shared_files.append("global_ex_calculator_gr.py")
        else:
            self.shared_files.append("matrix_calculator_temp_ex.py")
            self.shared_files.append("matrix_calculator_us_ex.py")
            self.shared_files.append("input_file_builder.py")
            self.shared_files.append("global_ex_calculator.py")

        self.shared_files.append(self.us_template)

        self.shared_files.append("salt_conc_pre_exec.py")
        self.shared_files.append("salt_conc_post_exec.py")

        if self.same_coordinates == False:
            for repl in replicas:
                if repl.coor_file not in self.shared_files:
                    self.shared_files.append(repl.coor_file)
        else:
            self.shared_files.append(replicas[0].coor_file)

        #-----------------------------------------------------------------------

        parm_url = 'file://%s' % (parm_path)
        self.shared_urls.append(parm_url)

        inp_url = 'file://%s' % (inp_path)
        self.shared_urls.append(inp_url)

        if self.group_exec == True:
            calc_temp_ex_url = 'file://%s' % (calc_temp_ex_path_gr)
            self.shared_urls.append(calc_temp_ex_url)

            calc_us_ex_url = 'file://%s' % (calc_us_ex_path_gr)
            self.shared_urls.append(calc_us_ex_url)

            global_calc_url = 'file://%s' % (global_calc_path_gr)
            self.shared_urls.append(global_calc_url)
        else:
            calc_temp_ex_url = 'file://%s' % (calc_temp_ex_path)
            self.shared_urls.append(calc_temp_ex_url)

            calc_us_ex_url = 'file://%s' % (calc_us_ex_path)
            self.shared_urls.append(calc_us_ex_url)

            build_inp_url = 'file://%s' % (build_inp_path)
            self.shared_urls.append(build_inp_url)

            global_calc_url = 'file://%s' % (global_calc_path)
            self.shared_urls.append(global_calc_url)

        rstr_template_url = 'file://%s' % (rstr_template_path)
        self.shared_urls.append(rstr_template_url)

        salt_pre_exec_url = 'file://%s' % (salt_pre_exec_path)
        self.shared_urls.append(salt_pre_exec_url)

        salt_post_exec_url = 'file://%s' % (salt_post_exec_path)
        self.shared_urls.append(salt_post_exec_url)

        if self.same_coordinates == False:
            for idx in range(7,len(self.shared_files)):
                cf_path = join(coor_path,self.shared_files[idx])
                coor_url = 'file://%s' % (cf_path)
                self.shared_urls.append(coor_url)
        else:
            cf_path = join(coor_path,replicas[0].coor_file)
            coor_url = 'file://%s' % (cf_path)
            self.shared_urls.append(coor_url)

    #---------------------------------------------------------------------------
    #                         
    def prepare_replica_for_md(self, dim_int, dim_str, replicas, replica, sd_shared_list):
       
        stage_out = []
        stage_in = []
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

        input_file = "%s_%d_%d.mdin" % (self.inp_basename, replica.id, (replica.cycle-1))
        output_file = "%s_%d_%d.mdout" % (self.inp_basename, replica.id, (replica.cycle-1))

        new_coor = replica.new_coor
        new_traj = replica.new_traj
        new_info = replica.new_info
        old_coor = replica.old_coor
        rid = replica.id

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

        replica_path = "replica_%d/" % (rid)

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
        
        if self.dims[dim_str]['type'] != 'salt':
            matrix_col = "matrix_column_%s_%s.dat" % (str(replica.id), str(replica.cycle-1))
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

        current_group = self.get_current_group_ids(dim_int, replicas, replica)

        #-----------------------------------------------------------------------
        # for all
        data = {
            "p1" : str(replica.dims['d1']['par']),
            "p2" : str(replica.dims['d2']['par']),
            "p3" : str(replica.dims['d3']['par']),
            "t1" : str(replica.dims['d1']['type']),
            "t2" : str(replica.dims['d2']['type']),
            "t3" : str(replica.dims['d3']['type']),
            "cycle_steps": str(self.cycle_steps),
            "new_restraints" : str(replica.new_restraints),
            "amber_input" : str(self.amber_input),
            "new_input_file" : str(new_input_file),
            "us_template": str(self.us_template),
            "cycle" : str(replica.cycle)
            }
        dump_data = json.dumps(data)
        json_pre_data_bash = dump_data.replace("\\", "")
        json_pre_data_sh   = dump_data.replace("\"", "\\\\\"")

        if self.dims[dim_str]['type'] == 'temperature':
            data = {
                "rid": str(replica.id),
                "replica_cycle" : str(replica.cycle-1),
                "base_name" : str(basename),
                "current_group" : current_group,
                "replicas" : str(len(replicas)),
                "amber_parameters": str(self.amber_parameters),
                "new_restraints" : str(replica.new_restraints),
                "init_temp" : str(replica.dims[dim_str]['par'])
                }

            dump_data = json.dumps(data)
            json_post_data_bash = dump_data.replace("\\", "")
            json_post_data_sh   = dump_data.replace("\"", "\\\\\"")

        #-----------------------------------------------------------------------

        if self.dims[dim_str]['type'] == 'umbrella':
            # IMPROVE!!!!!!!!!!!!!!!!!!
            current_group_rst = {}
            for repl in replicas:
                if str(repl.id) in current_group:
                    current_group_rst[str(repl.id)] = str(repl.new_restraints)

            base_restraint = self.us_template + "."

            data = {
                "rid": str(rid),
                "replica_cycle" : str(replica.cycle-1),
                "replicas" : str(self.replicas),
                "base_name" : str(basename),
                "init_temp" : str(replica.dims[dim_str]['par']),
                "amber_input" : str(self.amber_input),
                "amber_parameters": str(self.amber_parameters),
                "new_restraints" : str(replica.new_restraints),
                "current_group_rst" : current_group_rst
            }
            dump_data = json.dumps(data)
            json_post_data_bash = dump_data.replace("\\", "")
            json_post_data_sh   = dump_data.replace("\"", "\\\\\"")

        if self.dims[dim_str]['type'] == 'salt':
            # IMPROVE!!!!!!!!!!!!!!!!!!
            current_group_tsu = {}
            for repl in replicas:
                if str(repl.id) in current_group:
                    current_group_tsu[str(repl.id)] = [str(repl.dims[self.temperature_str]['par']), \
                                                       str(repl.dims[dim_str]['par']), \
                                                       str(repl.new_restraints)]

            data = {
                "rid": str(replica.id),
                "replica_cycle" : str(replica.cycle-1),
                "replicas" : str(self.replicas),
                "base_name" : str(basename),
                "init_temp" : str(replica.dims[dim_str]['par']),
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
            if self.dims[dim_str]['type'] == 'temperature':
                post_exec_str = "python matrix_calculator_temp_ex.py " + "\'" + json_post_data_bash + "\'"
            if self.dims[dim_str]['type'] == 'umbrella':
                post_exec_str = "python matrix_calculator_us_ex.py " + "\'" + json_post_data_bash + "\'"
        elif KERNELS[self.resource]["shell"] == "bourne":
            cu.executable = '/bin/sh'
            pre_exec_str = "python input_file_builder.py " + "\'" + json_pre_data_sh + "\'"
            if self.dims[dim_str]['type'] == 'temperature':
                post_exec_str = "python matrix_calculator_temp_ex.py " + "\'" + json_post_data_sh + "\'"
            if self.dims[dim_str]['type'] == 'umbrella':
                post_exec_str_us = "python matrix_calculator_us_ex.py " + "\'" + json_post_data_sh + "\'"

        if replica.cycle == 1:

            if (self.replica_gpu == True):
                amber_str = self.amber_path_gpu
            else:
                amber_str = self.amber_path    

            argument_str = " -O " + " -i " + new_input_file + " -o " + output_file + \
                           " -p " +  self.amber_parameters + " -c " + replica.coor_file + \
                           " -r " + new_coor + " -x " + new_traj + " -inf " + new_info  

            restraints_out = replica.new_restraints
            restraints_out_st = {
                'source': (replica.new_restraints),
                'target': 'staging:///%s' % (replica.new_restraints),
                'action': radical.pilot.COPY
            }
            stage_out.append(restraints_out_st)

            #-------------------------------------------------------------------
            # files needed to be staged in replica dir
            for i in range(2):
                stage_in.append(sd_shared_list[i])

            #-------------------------------------------------------------------            
            # replica coor
            repl_coor = replica.coor_file
            # index of replica_coor
            c_index = self.shared_files.index(repl_coor) 
            stage_in.append(sd_shared_list[c_index])

            #-------------------------------------------------------------------
            # input_file_builder.py
            stage_in.append(sd_shared_list[4])

            # restraint template file: ace_ala_nme_us.RST
            stage_in.append(sd_shared_list[6])

            if self.dims[dim_str]['type'] == 'temperature':
                # matrix_calculator_temp_ex.py
                stage_in.append(sd_shared_list[2])
            if self.dims[dim_str]['type'] == 'umbrella':    
                # matrix_calculator_us_ex.py
                stage_in.append(sd_shared_list[3])

            cu.arguments = ['-c', pre_exec_str + "; wait; " + amber_str + argument_str + "; wait; " + post_exec_str] 
            cu.pre_exec = self.pre_exec
            cu.cores = self.replica_cores
            cu.input_staging = stage_in
            cu.output_staging = stage_out
            cu.mpi = self.replica_mpi

        else:
            if (self.replica_gpu == True):
                amber_str = self.amber_path_gpu
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
            stage_in.append(sd_shared_list[4])
            
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

            #-------------------------------------------------------------------
            if self.dims[dim_str]['type'] == 'temperature':
                # matrix_calculator_temp_ex.py
                stage_in.append(sd_shared_list[2])
            if self.dims[dim_str]['type'] == 'umbrella':    
                # matrix_calculator_us_ex.py
                stage_in.append(sd_shared_list[3])

                new_coor_out = {
                    'source': new_coor,
                    'target': 'staging:///%s' % (replica_path + new_coor),
                    'action': radical.pilot.COPY
                }
                stage_out.append(new_coor_out)
               
            if self.dims[dim_str]['type'] != 'salt':
                cu.arguments = ['-c', pre_exec_str + "; wait; " + amber_str + argument_str + "; wait; " + post_exec_str]
            else:
                cu.arguments = ['-c', pre_exec_str + "; wait; " + amber_str + argument_str]
            cu.pre_exec = self.pre_exec
            cu.input_staging = stage_in
            cu.output_staging = stage_out
            cu.cores = self.replica_cores
            cu.mpi = self.replica_mpi
                   
        return cu

    #---------------------------------------------------------------------------
    #                     
    def prepare_group_for_md(self, dim_int, dim_str, group, sd_shared_list):

        #group.pop(0)
        group_id = group[0].group_idx[dim_int-1]

        stage_out = []
        stage_in  = []

        #-----------------------------------------------------------------------
        # files needed to be staged in replica dir
        for i in range(2):
            stage_in.append(sd_shared_list[i])

        # restraint template file: ace_ala_nme_us.RST
        stage_in.append(sd_shared_list[5])

        if (self.dims[dim_str]['type'] == 'temperature') and (self.nr_dims == 3):
            # remote_calculator_temp_ex_mpi.py file
            stage_in.append(sd_shared_list[2])
        if (self.dims[dim_str]['type'] == 'umbrella') and (self.nr_dims == 3):
            # remote_calculator_us_ex_mpi.py file
            stage_in.append(sd_shared_list[3])
            
        #----------------------------------------------------------------------- 
        #
        if self.same_coordinates == True:          
            # replica coor
            repl_coor = group[0].coor_file
            # index of replica_coor
            c_index = self.shared_files.index(repl_coor) 
            stage_in.append(sd_shared_list[c_index])

        data = {}
        data['gen_input'] = {}
        data['amber']     = {}
        data['amber']     = {'path': self.amber_path}
        data['ex']        = {}

        #if (self.dims[dim_str]['type'] == 'temperature'):
        #    data['ex']   = {}
        #if (self.dims[dim_str]['type'] == 'umbrella'):
        #    data['ex']    = {}
        
        basename = self.inp_basename
        substr = basename[:-5]
        len_substr = len(substr)
        #-----------------------------------------------------------------------
        # for all
        # assumption: all input files share a substring (ace_ala_nme)

        data['gen_input'] = {
            "steps": str(self.cycle_steps),
            "amber_inp" : str(self.amber_input[len_substr:]),
            "us_tmpl": str(self.us_template[len_substr:]),
            "cnr" : str(group[0].cycle),
            "base" : str(basename),
            "substr": str(substr),
            "replicas" : str(self.replicas),
            "amber_prm": str(self.amber_parameters[len_substr:]),
            "group_id": str(group_id)
            }

        for replica in group:
            # to generate in calculator:

            new_input_file = "%s_%d_%d.mdin" % (basename, replica.id, replica.cycle)
            output_file = "%s_%d_%d.mdout" % (self.inp_basename, replica.id, (replica.cycle))

            replica.new_coor = "%s_%d_%d.rst" % (basename, replica.id, replica.cycle)
            replica.new_traj = "%s_%d_%d.mdcrd" % (basename, replica.id, replica.cycle)
            replica.new_info = "%s_%d_%d.mdinfo" % (basename, replica.id, replica.cycle)

            new_coor = replica.new_coor
            new_traj = replica.new_traj
            new_info = replica.new_info

            replica.old_coor = "%s_%d_%d.rst" % (basename, replica.id, (replica.cycle-1))
            old_coor = replica.old_coor
           
            if (replica.cycle == 0):
                first_step = 0
            elif (replica.cycle == 1):
                first_step = int(self.cycle_steps)
            else:
                first_step = (replica.cycle - 1) * int(self.cycle_steps)
            
            rid = replica.id

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

            replica_path = "replica_%d/" % (rid)

            new_coor_out = {
                'source': new_coor,
                'target': 'staging:///%s' % (replica_path + new_coor),
                'action': radical.pilot.COPY
            }
            stage_out.append(new_coor_out)

            if self.us_template != '':
                out_string = "_%d.out" % (replica.cycle)
                rstr_out = {
                    'source': (replica.new_restraints + '.out'),
                    'target': 'staging:///%s' % (replica_path + replica.new_restraints + out_string),
                    'action': radical.pilot.COPY
                }
                stage_out.append(rstr_out)
            
            matrix_col = "matrix_column_%s_%s.dat" % (str(group_id), str(replica.cycle))
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

            #-------------------------------------------------------------------
            
            data['ex'][str(rid)] = {}
            if (dim_str == 'd1'):
                data['ex'][str(rid)] = {
                    "cd" : "1",
                    "p1" : str(replica.dims['d1']['par']),
                    "p2" : str(replica.dims['d2']['par']),
                    "p3" : str(replica.dims['d3']['par']),
                    "t1" : str(replica.dims['d1']['type']),
                    "t2" : str(replica.dims['d2']['type']),
                    "t3" : str(replica.dims['d3']['type']),
                    "new_rstr" : str(replica.new_restraints[len_substr:]),
                    "r_coor" : str(replica.coor_file[len_substr:])
                    }
            if (dim_str == 'd2'):
                data['ex'][str(rid)] = {
                    "cd" : "2",
                    "p1" : str(replica.dims['d1']['par']),
                    "p2" : str(replica.dims['d2']['par']),
                    "p3" : str(replica.dims['d3']['par']),
                    "t1" : str(replica.dims['d1']['type']),
                    "t2" : str(replica.dims['d2']['type']),
                    "t3" : str(replica.dims['d3']['type']),
                    "new_rstr" : str(replica.new_restraints[len_substr:]),
                    "r_coor" : str(replica.coor_file[len_substr:])
                    }
            if (dim_str == 'd3'):
                data['ex'][str(rid)] = {
                    "cd" : "3",
                    "p1" : str(replica.dims['d1']['par']),
                    "p2" : str(replica.dims['d2']['par']),
                    "p3" : str(replica.dims['d3']['par']),
                    "t1" : str(replica.dims['d1']['type']),
                    "t2" : str(replica.dims['d2']['type']),
                    "t3" : str(replica.dims['d3']['type']),
                    "new_rstr" : str(replica.new_restraints[len_substr:]),
                    "r_coor" : str(replica.coor_file[len_substr:])
                    }
            base_restraint = self.us_template + "."
            
            #-------------------------------------------------------------------
            if replica.cycle == 0:    
                restraints_out = replica.new_restraints
                restraints_out_st = {
                    'source': (replica.new_restraints),
                    'target': 'staging:///%s' % (replica.new_restraints),
                    'action': radical.pilot.COPY
                }
                stage_out.append(restraints_out_st)

                if self.same_coordinates == False: 
                    #-----------------------------------------------------------         
                    # replica coor
                    repl_coor = replica.coor_file
                    # index of replica_coor
                    c_index = self.shared_files.index(repl_coor) 
                    stage_in.append(sd_shared_list[c_index])
            else:
                #---------------------------------------------------------------
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

            replica.cycle += 1
        #-----------------------------------------------------------------------
        # data for input file generation 
        dump_data = json.dumps(data)
        json_data_bash = dump_data.replace("\\", "")
        json_data_sh   = dump_data.replace("\"", "\\\\\"")

        cu = radical.pilot.ComputeUnitDescription()

        if (self.dims[dim_str]['type'] == 'umbrella'):
            if KERNELS[self.resource]["shell"] == "bash":
                cu.executable = "python remote_calculator_us_ex_mpi.py " + "\'" + json_data_bash + "\'"
            elif KERNELS[self.resource]["shell"] == "bourne":
                cu.executable = "python remote_calculator_us_ex_mpi.py " + "\'" + json_data_sh + "\'"

        if (self.dims[dim_str]['type'] == 'temperature'):
            if KERNELS[self.resource]["shell"] == "bash":
                cu.executable = "python remote_calculator_temp_ex_mpi.py " + "\'" + json_data_bash + "\'"
            elif KERNELS[self.resource]["shell"] == "bourne":
                cu.executable = "python remote_calculator_temp_ex_mpi.py " + "\'" + json_data_sh + "\'"

        cu.pre_exec = self.pre_exec
        cu.input_staging = stage_in
        cu.output_staging = stage_out
        cu.cores = self.replica_cores
        cu.mpi = self.replica_mpi

        return cu

    #---------------------------------------------------------------------------
    #
    def prepare_replica_for_exchange(self, 
                                     dim_int, 
                                     dim_str, 
                                     replicas, 
                                     replica, 
                                     sd_shared_list):
        """
        should be used only for salt concentration exchange for 2d/3d
        """

        # name of the file which contains swap matrix column data for each replica
        basename = self.inp_basename
        matrix_col = "matrix_column_%s_%s.dat" % (str(replica.id), str(replica.cycle-1))
        current_group = self.get_current_group_ids(dim_int, replicas, replica)

        cu = radical.pilot.ComputeUnitDescription()
        
        current_group_tsu = {}
        for repl in replicas:
            if str(repl.id) in current_group:
                current_group_tsu[str(repl.id)] = [str(repl.dims[self.temperature_str]['par']), \
                                                   str(repl.dims[dim_str]['par']), \
                                                   str(repl.new_restraints)]

        data = {
            "rid": str(replica.id),
            "replica_cycle" : str(replica.cycle-1),
            "replicas" : str(self.replicas),
            "base_name" : str(basename),
            "init_temp" : str(replica.dims[self.temperature_str]['par']),
            "init_salt" : str(replica.dims[self.salt_str]['par']),
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
        in_list.append(sd_shared_list[1])
        in_list.append(sd_shared_list[4])
        in_list.append(sd_shared_list[5])

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
  
        out_list = []
        matrix_col_out = {
            'source': matrix_col,
            'target': 'staging:///%s' % (matrix_col),
            'action': radical.pilot.COPY
        }
        out_list.append(matrix_col_out)

        gr_size = self.dims[dim_str]['replicas']

        cu.input_staging = in_list
        cu.arguments = ['-ng', str(gr_size), '-groupfile', 'groupfile']
        cu.cores = gr_size
        cu.mpi = True
        cu.output_staging = out_list   

        return cu

    #---------------------------------------------------------------------------
    #
    def exchange_params(self, dim_str, replica_1, replica_2):
        
        if (self.dims[dim_str]['type'] == 'temperature'):
            temp = replica_2.dims[dim_str]['par']
            replica_2.dims[dim_str]['par'] = replica_1.dims[dim_str]['par']
            replica_1.dims[dim_str]['par'] = temp

        if (self.dims[dim_str]['type'] == 'umbrella'):
            rstr = replica_2.dims[dim_str]['par']
            replica_2.dims[dim_str]['par'] = replica_1.dims[dim_str]['par']
            replica_1.dims[dim_str]['par'] = rstr
            
            rstr = replica_2.new_restraints
            replica_2.new_restraints = replica_1.new_restraints
            replica_1.new_restraints = rstr

    #---------------------------------------------------------------------------
    #
    def do_exchange(self, current_cycle, dim_int, dim_str, replicas):

        r1 = None
        r2 = None
        cycle = replicas[0].cycle-1

        infile = "pairs_for_exchange_{dim}_{cycle}.dat".format(dim=dim_int, cycle=cycle)
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
                if self.exchange_off == False:
                    self.exchange_params(dim_str, r1, r2)
                    r1.swap = 1
                    r2.swap = 1
        except:
            raise

    #---------------------------------------------------------------------------
    #
    def prepare_global_ex_calc(self, GL, current_cycle, dim_int, dim_str, replicas, sd_shared_list):

        stage_out = []
        stage_in = []

        d1_type = self.dims['d1']['type']
        d2_type = self.dims['d2']['type']
        d3_type = self.dims['d3']['type']
        dims_string = d1_type + ' ' + d2_type + ' ' + d3_type

        group_nr = self.groups_numbers[dim_int-1]

        if GL == 1:
            cycle = replicas[0].cycle-1
        else:
            cycle = replicas[0].cycle
        
        if self.group_exec == True:
            # global_ex_calculator_gr.py file
            stage_in.append(sd_shared_list[4])
        else:
            # global_ex_calculator.py file
            stage_in.append(sd_shared_list[5])

        outfile = "pairs_for_exchange_{dim}_{cycle}.dat".format(dim=dim_int, cycle=cycle)
        stage_out.append(outfile)

        cu = radical.pilot.ComputeUnitDescription()
        cu.pre_exec = self.pre_exec
        cu.executable = "python"
        cu.input_staging  = stage_in
        if self.group_exec == True:
            cu.arguments = ["global_ex_calculator_gr.py", str(self.replicas), str(cycle), str(dim_int), str(group_nr), dims_string]
        else:
            cu.arguments = ["global_ex_calculator.py", str(self.replicas), str(cycle), str(dim_int), str(group_nr), dims_string]
        cu.cores = 1
        cu.mpi = False            
        cu.output_staging = stage_out

        return cu

    #---------------------------------------------------------------------------
    #
    def init_matrices(self, replicas):
 
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

        self.logger.debug("[init_matrices] d1_id_matrix: {0:s}".format(self.d1_id_matrix) )
        self.logger.debug("[init_matrices] d2_id_matrix: {0:s}".format(self.d2_id_matrix) )
        self.logger.debug("[init_matrices] d3_id_matrix: {0:s}".format(self.d3_id_matrix) )

        # temp_matrix
        for r in replicas:
            row = []
            row.append(r.id)
            row.append(r.new_temperature)
            for c in range(self.nr_cycles - 1):
                row.append( -1.0 )

            self.temp_matrix.append( row )

        self.temp_matrix = sorted(self.temp_matrix)
        self.logger.debug("[init_matrices] temp_matrix: {0:s}".format(self.temp_matrix) )

        # us_d1_matrix
        for r in replicas:
            row = []
            row.append(r.id)
            row.append(r.new_restraints)
            for c in range(self.nr_cycles - 1):
                row.append( -1.0 )
            self.us_d1_matrix.append( row )

        self.us_d1_matrix = sorted(self.us_d1_matrix)
        self.logger.debug("[init_matrices] us_d1_matrix: {0:s}".format(self.us_d1_matrix) )
        """
        pass

    #---------------------------------------------------------------------------
    #
    def get_current_group_ids(self, dim_int, replicas, replica):

        current_group = []
        for r1 in replicas:
            if dim_int == 1:
                r1_pair = [r1.dims['d2']['par'], r1.dims['d3']['par']]
                my_pair = [replica.dims['d2']['par'], replica.dims['d3']['par']]  
                if r1_pair == my_pair:
                    current_group.append(str(r1.id))

            elif dim_int == 2:
                r1_pair = [r1.dims['d1']['par'], r1.dims['d3']['par']]
                my_pair = [replica.dims['d1']['par'], replica.dims['d3']['par']]
                if r1_pair == my_pair:
                    current_group.append(str(r1.id))

            elif dim_int == 3:
                r1_pair = [r1.dims['d1']['par'], r1.dims['d2']['par']]
                my_pair = [replica.dims['d1']['par'], replica.dims['d2']['par']]
                if r1_pair == my_pair:
                    current_group.append(str(r1.id))

        return current_group

    #---------------------------------------------------------------------------
    #
    def get_all_groups(self, dim_int, replicas):

        dim = dim_int-1
        all_groups = []
        for i in range(self.groups_numbers[dim]):
            all_groups.append([None])
        for r in replicas:
            all_groups[r.group_idx[dim]].append(r)

        return all_groups

