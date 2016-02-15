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
import amber_kernels_3d_tuu.input_file_builder
import amber_kernels_3d_tuu.global_ex_calculator
from replicas.replica import Replica3d

#-------------------------------------------------------------------------------
#
class KernelPatternS3dTUU(object):
    """TODO
    """
    def __init__(self, inp_file, rconfig, work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as 
        specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        self.name = 'ak-patternB-3d-TUU'
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

        # assigning parameters:
        dim_params = {}
        for k in self.dims:
            if self.dims[k]['type'] == 'temperature':
                dim_params[k] = []
                N = self.dims[k]['replicas']
                factor = (self.dims[k]['temp_end']/self.dims[k]['temp_start'])**(1./(N-1))
                for n in range(N):
                    new_temp = self.dims[k]['temp_start'] * (factor**n)
                    dim_params[k].append(new_temp)
            if self.dims[k]['type'] == 'umbrella':
                dim_params[k] = []
                for i in range(self.dims[k]['replicas']):
                    spacing = (self.dims[k]['us_end'] - self.dims[k]['us_start']) / (float(self.dims[k]['replicas'])-1)
                    starting_value = self.dims[k]['us_start'] + i*spacing
                    dim_params[k].append(starting_value)

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

        return replicas

    #---------------------------------------------------------------------------
    #
    def prepare_shared_data(self, replicas):

        coor_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_coordinates_path
        parm_path = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_parameters
        inp_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_input

        # for 3d only, check
        calc_temp_ex = os.path.dirname(amber_kernels_3d_tuu.remote_calculator_temp_ex_mpi.__file__)
        calc_temp_ex_path = calc_temp_ex + "/remote_calculator_temp_ex_mpi.py"

        # for 3d only, check
        calc_us_ex = os.path.dirname(amber_kernels_3d_tuu.remote_calculator_us_ex_mpi.__file__)
        calc_us_ex_path = calc_us_ex + "/remote_calculator_us_ex_mpi.py"

        # for 3d only, check
        global_calc = os.path.dirname(amber_kernels_3d_tuu.global_ex_calculator.__file__)
        global_calc_path = global_calc + "/global_ex_calculator.py"

        rstr_template_path = self.work_dir_local + "/" + self.input_folder + "/" + self.us_template

        #-----------------------------------------------------------------------
        self.shared_files.append(self.amber_parameters)
        self.shared_files.append(self.amber_input)

        # for 3d only, check
        self.shared_files.append("remote_calculator_temp_ex_mpi.py")
        self.shared_files.append("remote_calculator_us_ex_mpi.py")
        self.shared_files.append("global_ex_calculator.py")

        self.shared_files.append(self.us_template)
     
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

        calc_temp_ex_url = 'file://%s' % (calc_temp_ex_path)
        self.shared_urls.append(calc_temp_ex_url)

        calc_us_ex_url = 'file://%s' % (calc_us_ex_path)
        self.shared_urls.append(calc_us_ex_url)

        global_calc_url = 'file://%s' % (global_calc_path)
        self.shared_urls.append(global_calc_url)

        rstr_template_url = 'file://%s' % (rstr_template_path)
        self.shared_urls.append(rstr_template_url)

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
    def prepare_group_for_md(self, dimension, group, sd_shared_list):

        group.pop(0)
        group_id = group[0].group_idx[dimension-1]

        stage_out = []
        stage_in = []

        #-----------------------------------------------------------------------
        # files needed to be staged in replica dir
        for i in range(2):
            stage_in.append(sd_shared_list[i])

        # restraint template file: ace_ala_nme_us.RST
        stage_in.append(sd_shared_list[5])

        if (self.dims[dimension]['type'] == 'temperature') and (self.nr_dims == 3):
            # remote_calculator_temp_ex_mpi.py file
            stage_in.append(sd_shared_list[2])
        if (self.dims[dimension]['type'] == 'umbrella') and (self.nr_dims == 3):
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

        if (self.dims[dimension]['type'] == 'temperature'):
            data['ex_temp']   = {}
        if (self.dims[dimension]['type'] == 'umbrella'):
            data['ex_us']     = {}
        
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

            self.us_template != '':
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
            if (self.dims[dimension] == 'd1':
                data['ex'][str(rid)] = {
                    "cd" : "d1",
                    "d1" : str(replica.dims['d1']['par']),
                    "d2" : str(replica.dims['d2']['par']),
                    "d3" : str(replica.dims['d3']['par']),
                    "new_rstr" : str(replica.new_restraints[len_substr:]),
                    "r_coor" : str(replica.coor_file[len_substr:])
                    }
            if (self.dims[dimension] == 'd2':
                data['ex'][str(rid)] = {
                    "cd" : "d2",
                    "d1" : str(replica.dims['d1']['par']),
                    "d2" : str(replica.dims['d2']['par']),
                    "d3" : str(replica.dims['d3']['par']),
                    "new_rstr" : str(replica.new_restraints[len_substr:]),
                    "r_coor" : str(replica.coor_file[len_substr:])
                    }
            if (self.dims[dimension] == 'd3':
                data['ex'][str(rid)] = {
                    "cd" : "d3",
                    "d1" : str(replica.dims['d1']['par']),
                    "d2" : str(replica.dims['d2']['par']),
                    "d3" : str(replica.dims['d3']['par']),
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

        if (self.dims[dimension]['type'] == 'umbrella'):
            if KERNELS[self.resource]["shell"] == "bash":
                cu.executable = "python remote_calculator_us_ex_mpi.py " + "\'" + json_data_bash + "\'"
            elif KERNELS[self.resource]["shell"] == "bourne":
                cu.executable = "python remote_calculator_us_ex_mpi.py " + "\'" + json_data_sh + "\'"

        if (self.dims[dimension]['type'] == 'temperature'):
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
    def exchange_params(self, dimension, replica_1, replica_2):
        
        if (self.dims[dimension]['type'] == 'temperature'):
            temp = replica_2.dims[dimension]['par']
            replica_2.dims[dimension]['par'] = replica_1.dims[dimension]['param']
            replica_1.dims[dimension]['par'] = temp

        if (self.dims[dimension]['type'] == 'umbrella'):
            rstr = replica_2.dims[dimension]['par']
            replica_2.dims[dimension]['par'] = replica_1.dims[dimension]['param']
            replica_1.dims[dimension]['par'] = rstr
            
            rstr = replica_2.new_restraints
            replica_2.new_restraints = replica_1.new_restraints
            replica_1.new_restraints = rstr

    #---------------------------------------------------------------------------
    #
    def do_exchange(self, current_cycle, dimension, replicas):
        """
        """

        r1 = None
        r2 = None

        cycle = replicas[0].cycle-1

        infile = "pairs_for_exchange_{dim}_{cycle}.dat".format(dim=dimension, cycle=cycle)
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
                    self.exchange_params(dimension, r1, r2)
                    r1.swap = 1
                    r2.swap = 1
        except:
            raise

    #---------------------------------------------------------------------------
    #
    def prepare_global_ex_calc(self, GL, current_cycle, dimension, replicas, sd_shared_list):

        stage_out = []
        stage_in = []
 
        group_nr = self.groups_numbers[dimension-1]

        if GL == 1:
            cycle = replicas[0].cycle-1
        else:
            cycle = replicas[0].cycle
        
        # global_ex_calculator.py file
        stage_in.append(sd_shared_list[4])

        outfile = "pairs_for_exchange_{dim}_{cycle}.dat".format(dim=dimension, cycle=cycle)
        stage_out.append(outfile)

        cu = radical.pilot.ComputeUnitDescription()
        cu.pre_exec = self.pre_exec
        cu.executable = "python"
        cu.input_staging  = stage_in
        cu.arguments = ["global_ex_calculator.py", str(self.replicas), str(cycle), str(dimension), str(group_nr)]
        cu.cores = 1
        cu.mpi = False            
        cu.output_staging = stage_out

        return cu

    #---------------------------------------------------------------------------
    #
    def init_matrices(self, replicas):
        """
        DOES NOT WORK!
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

    #---------------------------------------------------------------------------
    #
    def get_current_group(self, dimension, replicas, replica):
        """
        """

        current_group = []

        for r1 in replicas:
            
            ###############################################
            # temperature exchange
            if dimension == 2:
                
                r1_pair = [r1.rstr_val_1, r1.rstr_val_2]
                my_pair = [replica.rstr_val_1, replica.rstr_val_2]
                  
                if r1_pair == my_pair:
                    current_group.append(str(r1.id))

            ###############################################
            # us exchange d1
            elif dimension == 1:
                r1_pair = [r1.new_temperature, r1.rstr_val_2]
                my_pair = [replica.new_temperature, replica.rstr_val_2]

                if r1_pair == my_pair:
                    current_group.append(str(r1.id))

            ###############################################
            # us exchange d3
            elif dimension == 3:
                r1_pair = [r1.new_temperature, r1.rstr_val_1]
                my_pair = [replica.new_temperature, replica.rstr_val_1]

                if r1_pair == my_pair:
                    current_group.append(str(r1.id))

        return current_group

    #---------------------------------------------------------------------------
    #
    def get_all_groups(self, dim, replicas):

        dim = dim-1
        all_groups = []
        for i in range(self.groups_numbers[dim]):
            all_groups.append([None])

        for r in replicas:
            all_groups[r.group_idx[dim]].append(r)

        return all_groups

