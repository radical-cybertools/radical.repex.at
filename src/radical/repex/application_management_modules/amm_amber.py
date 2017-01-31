"""
.. module:: radical.repex.application_management_modules.amm_amber
.. moduleauthor::  <antons.treikalis@gmail.com>
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
import pickle
import tarfile
import datetime
from os import path
from os import listdir
from os.path import join
import radical.pilot as rp
from os.path import isfile
import radical.utils.logger as rul
from kernels.kernels import KERNELS
import ram_amber.input_file_builder
from replicas.replica import Replica
from repex_utils.simulation_restart import Restart

#-------------------------------------------------------------------------------
#
class AmmAmber(object):
    """Application management Module (AMM) for Amber kernel. For each simulation 
    should be created only a single instance of AMM. 

    Attributes:
        Way too many

    """
    def __init__(self, 
                 inp_file, 
                 rconfig, 
                 work_dir_local):
        """
        Args:
            inp_file - simulation input file with parameters specified by user 

            rconfig - resource configuration file
            
            work_dir_local - directory from which main simulation script was invoked
        """

        self.name = 'AmmAmber.log'
        self.logger  = rul.get_logger ('radical.repex', self.name)

        self.resource         = rconfig.get('resource')
        self.inp_basename     = inp_file['remd.input'].get('input_file_basename')
        self.input_folder     = inp_file['remd.input'].get('input_folder')
        self.us_template      = inp_file['remd.input'].get('us_template', '') 
        self.init_temp        = float(inp_file['remd.input'].get('init_temperature', '-1.0') )
        self.amber_parameters = inp_file['remd.input'].get('amber_parameters')
        self.amber_input      = inp_file['remd.input'].get('amber_input')
        self.work_dir_local   = work_dir_local
        self.current_cycle    = -1

        # for restart
        self.restart           = inp_file['remd.input'].get('restart', 'False')
        self.restart_file      = inp_file['remd.input'].get('restart_file', '')
        if self.restart == 'True':
            self.restart = True
            self.restart_done = False
        else:
            self.restart = False
            self.restart_done = True

        if ( (self.restart == True) and (self.restart_file == '') ):
            self.logger.info("If simulation is restarted, name of the restart_file must be specified, exiting...")
            sys.exit(1)

        self.cores           = int(rconfig.get('cores', '1'))
        self.cycle_steps     = int(inp_file['remd.input'].get('steps_per_cycle'))
        self.nr_cycles       = int(inp_file['remd.input'].get('number_of_cycles','1'))
        self.replica_cores   = int(inp_file['remd.input'].get('replica_cores', '1'))
        #self.nr_ex_neighbors = int(inp_file['remd.input'].get('nr_exchange_neighbors', '1'))

        self.group_exec = inp_file['remd.input'].get('group_exec', 'False')
        if self.group_exec == 'True':
            self.group_exec = True
        else:
            self.group_exec = False

        if inp_file['remd.input'].get('replica_gpu') == "True":
            self.replica_gpu = True
        else:
            self.replica_gpu = False

        # if True, we do global MPI for 1D cases (umbrella and temperature)
        # Note: must be set to True for Execution Mode II
        if inp_file['remd.input'].get('exchange_mpi', 'False') == "True":
            self.exchange_mpi = True
        else:
            self.exchange_mpi = False

        self.exchange_mpi_cores = int(inp_file['remd.input'].get('exchange_mpi_cores', 0))
           
        #-----------------------------------------------------------------------
    
        self.amber_coordinates_path = inp_file['remd.input'].get('amber_coordinates_folder')
        if inp_file['remd.input'].get('same_coordinates', 'True') == "True":
            self.same_coordinates = True
        else:
            self.same_coordinates = False

        if inp_file['remd.input'].get('download_mdinfo', 'False') == 'True':
            self.down_mdinfo = True
        else:
            self.down_mdinfo = False
     
        if inp_file['remd.input'].get('download_mdout', 'False') == 'True':
            self.down_mdout = True
        else:
            self.down_mdout = False

        if inp_file['remd.input'].get('copy_mdinfo', 'False') == 'True':
            self.copy_mdinfo = True
        else:
            self.copy_mdinfo = False

        if inp_file['remd.input'].get('replica_mpi', 'False') == "True":
            self.replica_mpi = True
        else:
            self.replica_mpi = False   
    
        if ((self.replica_mpi == False) and (self.replica_cores > 1)):
            self.logger.info("If replica_cores is greater than 1 replica_mpi must be set to True, exiting...")
            sys.exit(1)

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
        if self.dims['d1']['replicas'] and (not self.dims['d2']['replicas']) \
        and (not self.dims['d3']['replicas']):
            self.nr_dims = 1
        if self.dims['d1']['replicas'] and self.dims['d2']['replicas'] \
        and (not self.dims['d3']['replicas']):
            self.nr_dims = 2
        if self.dims['d1']['replicas'] and self.dims['d2']['replicas'] \
        and self.dims['d3']['replicas']:
            self.nr_dims = 3

        if self.nr_dims == 0:
            self.logger.info("Number of dimensions must be greater than 0, exiting...")
            sys.exit(1) 

        self.exchange_off = []
        for d in range(self.nr_dims):
            d_str = 'd' + str(d+1) 
            if (inp_file['dim.input'][d_str].get("exchange_off", "False")) == "True":
                self.exchange_off.append(True)
            else:
                self.exchange_off.append(False)

        if self.nr_dims == 1:
            self.replicas = self.dims['d1']['replicas']
            self.ex_accept_id_matrix_d1 = []
        elif self.nr_dims == 2:
            self.replicas = self.dims['d1']['replicas'] * self.dims['d2']['replicas']
            self.ex_accept_id_matrix_d1 = []
            self.ex_accept_id_matrix_d2 = []
        elif self.nr_dims == 3:
            self.replicas = self.dims['d1']['replicas'] * \
            self.dims['d2']['replicas'] * self.dims['d3']['replicas']
            self.ex_accept_id_matrix_d1 = []
            self.ex_accept_id_matrix_d2 = []
            self.ex_accept_id_matrix_d3 = []   

        self.restraints_files = []
        for k in range(self.replicas):
            self.restraints_files.append(self.us_template + "." + str(k) )
 
        for k in self.dims:
            if self.dims[k]['type'] == 'umbrella':
                self.dims[k]['us_start'] = float(inp_file['dim.input'][k].get('min_umbrella'))
                self.dims[k]['us_end'] = float(inp_file['dim.input'][k].get('max_umbrella'))
            if self.dims[k]['type'] == 'temperature':
                self.dims[k]['temp_start'] = float(inp_file['dim.input'][k].get('min_temperature'))
                self.dims[k]['temp_end'] = float(inp_file['dim.input'][k].get('max_temperature'))
            if self.dims[k]['type'] == 'salt':
                self.dims[k]['salt_start'] = float(inp_file['dim.input'][k].get('min_salt'))
                self.dims[k]['salt_end'] = float(inp_file['dim.input'][k].get('max_salt'))

        #-----------------------------------------------------------------------

        self.pre_exec = KERNELS[self.resource]["kernels"]\
                        ["amber"].get("pre_execution")

        self.amber_path     = inp_file['remd.input'].get('amber_path')
        self.amber_path_mpi = inp_file['remd.input'].get('amber_path_mpi')
        if self.amber_path == None:
            self.logger.info("Using default Amber path for: {0}".format(rconfig.get('resource')))
            self.amber_path = KERNELS[self.resource]["kernels"]["amber"].get("executable")
            self.amber_path_mpi = KERNELS[self.resource]["kernels"]["amber"].get("executable_mpi")
            self.amber_path_gpu = KERNELS[self.resource]["kernels"]["amber"].get("executable_gpu")
        if self.amber_path == None:
            self.logger.info("Amber (sander) path can't be found, looking for sander.MPI")
            if self.amber_path_mpi == None:
                self.logger.info("Amber (sander.MPI) path can't be found, exiting...")
            sys.exit(1)

        self.shared_urls = []
        self.shared_files = []     

        self.salt_str = ''
        self.temperature_str = ''
        self.umbrella = False
        for d_str in self.dims:
            if self.dims[d_str]['type'] == 'temperature':
                self.temperature_str = d_str
            if self.dims[d_str]['type'] == 'salt':
                self.salt_str = d_str
            if self.dims[d_str]['type'] == 'umbrella':
                self.umbrella = True

        self.groups_numbers = [0, 0, 0] 

        if ( (self.umbrella == True) and (self.us_template == '') ):
            self.logger.info("For umbrella exchange simulations must be specified us_template parameter, exiting...")
            sys.exit(1)

    #---------------------------------------------------------------------------
    #
    @staticmethod
    def get_rstr_id(restraint):
        """extracts restraint index from a given restraint file

        Args:
            restraint - name of the restraint file

        Returns:
            integer representing index of a given restraint file
        """
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
    def save_replicas(self, 
                      current_cycle, 
                      dim_int, 
                      dim_str, 
                      replicas):
        """Saves the state of the simulation and state of replicas to .pkl file. 
        Method is called after every simulation cycle and for each dimension in 
        the current simulation. Method first updates restart object, writes 
        state of replicas to .pkl file and then writes restart object (which 
        represents simulation state) to .pkl file

        Args:
            current_cycle - current simulation cycle

            dim_int - integer representing the index of the current dimension

            dim_str - string representing the index of the current dimension

            replicas - list of replica objects

        Returns:
            None
        """

        self.restart_object.dimension     = dim_int
        self.restart_object.current_cycle =  current_cycle
        self.restart_object.old_sandbox   = self.restart_object.new_sandbox

        self.restart_file = 'simulation_objects_{0}_{1}.pkl'.format( dim_int, current_cycle )
        with open(self.restart_file, 'wb') as output:
            for replica in replicas:
                pickle.dump(replica, output, pickle.HIGHEST_PROTOCOL)

            pickle.dump(self.restart_object, output, pickle.HIGHEST_PROTOCOL)

    #---------------------------------------------------------------------------
    #
    def recover_replicas(self):
        """Recovers the state of the failed simulation from .pkl file. Updates 
        restart_object of this AMM. Updates groups_numbers attribute of this 
        AMM.  

        Args:
            None

        Returns:
            list of recovered replica objects
        """

        replicas = []
        with open(self.restart_file, 'rb') as input:
            for i in range(self.replicas):
                r_temp = pickle.load(input)
                replicas.append( r_temp )
            self.restart_object = pickle.load(input)
            self.groups_numbers = self.restart_object.groups_numbers
        return replicas

    #---------------------------------------------------------------------------
    #
    def initialize_replicas(self):
        """Initializes replicas with parameters specified in simulation input
        file. Assigns group index in each dimension for each initialized replica
        using assign_group_idx(). initializes a restart object of this 
        application management module.  

        Args:
            None

        Returns:
            list of replica objects
        """
        self.restart_object = Restart()

        # parse coor file
        coor_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_coordinates_path
        coor_list  = listdir(coor_path)
        base = coor_list[0]
        self.coor_basename = base.split('inpcrd')[0]+'inpcrd'

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

                        re = Replica(rid, \
                                    new_restraints=r, \
                                    coor=coor_file,
                                    d1_param=float(dim_params['d1'][i]), \
                                    d2_param=float(dim_params['d2'][j]), \
                                    d3_param=float(dim_params['d3'][k]), \
                                    d1_type = self.dims['d1']['type'], \
                                    d2_type = self.dims['d2']['type'], \
                                    d3_type = self.dims['d3']['type'], \
                                    nr_dims = self.nr_dims)
                        replicas.append(re)

            self.assign_group_idx(replicas, 1)
            self.assign_group_idx(replicas, 2)
            self.assign_group_idx(replicas, 3)

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

                    re = Replica(rid, \
                                new_restraints=r, \
                                coor=coor_file,
                                d1_param=float(dim_params['d1'][i]), \
                                d2_param=float(dim_params['d2'][j]), \
                                d1_type = self.dims['d1']['type'], \
                                d2_type = self.dims['d2']['type'], \
                                nr_dims = self.nr_dims)
                    replicas.append(re)

            self.assign_group_idx(replicas, 1)
            self.assign_group_idx(replicas, 2)

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

                re = Replica(rid, \
                            new_restraints=r, \
                            coor=coor_file,
                            d1_param=float(dim_params['d1'][i]), \
                            d1_type = self.dims['d1']['type'], \
                            nr_dims = self.nr_dims)
                replicas.append(re)

            self.assign_group_idx(replicas, 1)

        return replicas

    #---------------------------------------------------------------------------
    #
    def assign_group_idx(self, replicas, dim_int):
        """assigns to each replica a group index in current dimension (specified
        by dim_int) Updates groups_numbers attribute of this AMM. Updates 
        groups_numbers attribute of the restart object.   

        Args:
            replicas - list of replica objects

            dim-int - integer representing the index of current dimension

        Returns:
            None
        """

        if self.nr_dims == 3:

            if dim_int == 1:
                g_d1 = []
                for r in replicas:
                    updated = False
                    if len(g_d1) == 0:
                        g_d1.append([r.dims['d2']['par'], r.dims['d3']['par']]) 
                    for i,j in enumerate(g_d1):
                        if (g_d1[i][0] == r.dims['d2']['par']) and (g_d1[i][1] == r.dims['d3']['par']):
                            r.group_idx[0] = i
                            updated = True
                    if updated == False:
                        g_d1.append([r.dims['d2']['par'], r.dims['d3']['par']])
                        r.group_idx[0] = len(g_d1) - 1
                self.groups_numbers[0] = len(g_d1)

            if dim_int == 2:
                g_d2 = []
                for r in replicas:
                    updated = False
                    if len(g_d2) == 0:
                        g_d2.append([r.dims['d1']['par'], r.dims['d3']['par']]) 
                    for i,j in enumerate(g_d2):
                        if (g_d2[i][0] == r.dims['d1']['par']) and (g_d2[i][1] == r.dims['d3']['par']):
                            r.group_idx[1] = i
                            updated = True
                    if updated == False:
                        g_d2.append([r.dims['d1']['par'], r.dims['d3']['par']])
                        r.group_idx[1] = len(g_d2) - 1
                self.groups_numbers[1] = len(g_d2)

            if dim_int == 3:
                g_d3 = []
                for r in replicas:
                    updated = False
                    if len(g_d3) == 0:
                        g_d3.append([r.dims['d1']['par'], r.dims['d2']['par']])
                    for i,j in enumerate(g_d3):
                        if (g_d3[i][0] == r.dims['d1']['par']) and (g_d3[i][1] == r.dims['d2']['par']):
                            r.group_idx[2] = i
                            updated = True
                    if updated == False:
                        g_d3.append([r.dims['d1']['par'], r.dims['d2']['par']])
                        r.group_idx[2] = len(g_d3) - 1
                self.groups_numbers[2] = len(g_d3)

        if self.nr_dims == 2:
            if dim_int == 1:
                g_d1 = []
                for r in replicas:
                    updated = False
                    if len(g_d1) == 0:
                        g_d1.append(r.dims['d2']['par'])
                    for i,j in enumerate(g_d1):
                        if (g_d1[i] == r.dims['d2']['par']):
                            r.group_idx[0] = i
                            updated = True
                    if updated == False:
                        g_d1.append(r.dims['d2']['par'])
                        r.group_idx[0] = len(g_d1) - 1
                self.groups_numbers[0] = len(g_d1) 

            if dim_int == 2:
                g_d2 = []
                for r in replicas:
                    updated = False
                    if len(g_d2) == 0:
                        g_d2.append(r.dims['d1']['par']) 
                            
                    for i,j in enumerate(g_d2):
                        if (g_d2[i] == r.dims['d1']['par']):
                            r.group_idx[1] = i
                            updated = True
                    if updated == False:
                        g_d2.append(r.dims['d1']['par'])
                        r.group_idx[1] = len(g_d2) - 1
                self.groups_numbers[1] = len(g_d2) 

        if self.nr_dims == 1:
            for r in replicas:
                r.group_idx[0] = 0
            self.groups_numbers = [1] 

        self.restart_object.groups_numbers = self.groups_numbers
               
    #---------------------------------------------------------------------------
    #
    def prepare_shared_data(self, replicas):
        """Populates shared_files list (an attribute of this AMM) with names 
        of the input files which must be transferred to the remote system for 
        a given simulation. Populates shared_urls list (an attribute of this 
        AMM) with paths to input files which must be transferred to the remote 
        system for a given simulation.

        Args:
            replicas - list of replica objects

        Returns:
            None
        """

        coor_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_coordinates_path
        parm_path = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_parameters
        inp_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_input

        rams_path = os.path.dirname(ram_amber.input_file_builder.__file__)

        #-----------------------------------------------------------------------
        # for group exec only
        
        calc_temp_ex_path_gr = rams_path + "/matrix_calculator_temp_ex_mpi.py"
        calc_us_ex_path_gr   = rams_path + "/matrix_calculator_us_ex_mpi.py"
        global_calc_path_gr  = rams_path + "/global_ex_calculator_gr.py"
        
        #-----------------------------------------------------------------------

        calc_temp_ex_path = rams_path + "/matrix_calculator_temp_ex.py"
        calc_us_ex_path   = rams_path + "/matrix_calculator_us_ex.py"

        global_calc_path         = rams_path + "/global_ex_calculator.py"
        global_calc_temp_ex_path = rams_path + "/global_ex_calculator_temp_ex.py"
        global_calc_us_ex_path   = rams_path + "/global_ex_calculator_us_ex.py"
        calc_temp_ex_mpi_path    = rams_path + "/global_ex_calculator_tex_mpi.py"
        calc_us_ex_mpi_path      = rams_path + "/global_ex_calculator_us_mpi.py"

        rstr_template_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.us_template

        build_inp_path      = rams_path + "/input_file_builder.py"
        salt_pre_exec_path  = rams_path + "/salt_conc_pre_exec.py"
        salt_post_exec_path = rams_path + "/salt_conc_post_exec.py"

        #-----------------------------------------------------------------------
        # now adding to shared_files:

        self.shared_files.append(self.amber_parameters)
        self.shared_files.append(self.amber_input)

        if self.group_exec == True:
            self.shared_files.append("matrix_calculator_temp_ex_mpi.py")
            self.shared_files.append("matrix_calculator_us_ex_mpi.py")
            self.shared_files.append("global_ex_calculator_gr.py")
        elif self.exchange_mpi == False:
            self.shared_files.append("matrix_calculator_temp_ex.py")
            self.shared_files.append("matrix_calculator_us_ex.py")
            self.shared_files.append("input_file_builder.py")
            self.shared_files.append("global_ex_calculator.py")
            self.shared_files.append("global_ex_calculator_temp_ex.py")
            self.shared_files.append("global_ex_calculator_us_ex.py")
        elif self.exchange_mpi == True:
            self.shared_files.append("global_ex_calculator_tex_mpi.py")
            self.shared_files.append("global_ex_calculator_us_mpi.py")
            self.shared_files.append("input_file_builder.py")

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
        #
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
        elif self.exchange_mpi == False:
            calc_temp_ex_url = 'file://%s' % (calc_temp_ex_path)
            self.shared_urls.append(calc_temp_ex_url)

            calc_us_ex_url = 'file://%s' % (calc_us_ex_path)
            self.shared_urls.append(calc_us_ex_url)

            build_inp_url = 'file://%s' % (build_inp_path)
            self.shared_urls.append(build_inp_url)

            global_calc_url = 'file://%s' % (global_calc_path)
            self.shared_urls.append(global_calc_url)

            global_calc_url_t = 'file://%s' % (global_calc_temp_ex_path)
            self.shared_urls.append(global_calc_url_t)

            global_calc_url_u = 'file://%s' % (global_calc_us_ex_path)
            self.shared_urls.append(global_calc_url_u)
        elif self.exchange_mpi == True:
            calc_temp_ex_mpi_url = 'file://%s' % (calc_temp_ex_mpi_path)
            self.shared_urls.append(calc_temp_ex_mpi_url)

            calc_us_ex_mpi_url = 'file://%s' % (calc_us_ex_mpi_path)
            self.shared_urls.append(calc_us_ex_mpi_url)

            build_inp_url = 'file://%s' % (build_inp_path)
            self.shared_urls.append(build_inp_url)

        rstr_template_url = 'file://%s' % (rstr_template_path)
        self.shared_urls.append(rstr_template_url)

        salt_pre_exec_url = 'file://%s' % (salt_pre_exec_path)
        self.shared_urls.append(salt_pre_exec_url)

        salt_post_exec_url = 'file://%s' % (salt_post_exec_path)
        self.shared_urls.append(salt_post_exec_url)

        if self.same_coordinates == False:
            for idx in range(9,len(self.shared_files)):
                cf_path = join(coor_path,self.shared_files[idx])
                coor_url = 'file://%s' % (cf_path)
                self.shared_urls.append(coor_url)
        else:
            cf_path = join(coor_path,replicas[0].coor_file)
            coor_url = 'file://%s' % (cf_path)
            self.shared_urls.append(coor_url)

    #---------------------------------------------------------------------------
    #                         
    def prepare_replica_for_md(self, 
                               current_cycle,
                               dim_int, 
                               dim_str, 
                               group, 
                               replica, 
                               sd_shared_list):

        """Prepares RPs compute unit for a given replica to run MD simulation. 

        Args:
            current_cycle - integer representing number of the current 
            simulation cycle

            dim_int - integer representing the index of the current dimension

            dim_str - string representing the index of the current dimension

            group - list of replica objects which are in the same group with 
            a given replica in current dimension

            replica - replica object for which we are preparing RPs compute unit

            sd_shared_list - list of RPs data directives corresponding to 
            simulation input files

        Returns:
            RPs compute unit
        """

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
        replica.sim_cycle = current_cycle

        input_file = "%s_%d_%d.mdin" % (self.inp_basename, replica.id, (replica.cycle-1))
        output_file = "%s_%d_%d.mdout" % (self.inp_basename, replica.id, (replica.cycle-1))

        new_coor = replica.new_coor
        new_traj = replica.new_traj
        new_info = replica.new_info
        old_coor = replica.old_coor
        rid      = replica.id

        replica_path = "replica_%d/" % (rid)

        if (self.down_mdinfo == True):
            info_local = {
                'source':   new_info,
                'target':   new_info,
                'action':   rp.TRANSFER
            }
            stage_out.append(info_local)

        if (self.down_mdout == True):
            output_local = {
                'source':   output_file,
                'target':   output_file,
                'action':   rp.TRANSFER
            }
            stage_out.append(output_local)

        if (self.copy_mdinfo == True):
            info_out = {
                'source': new_info,
                'target': 'staging:///%s' % (replica_path + new_info),
                'action': rp.COPY
            }
            stage_out.append(info_out)

        new_coor_out = {
            'source': new_coor,
            'target': 'staging:///%s' % (replica_path + new_coor),
            'action': rp.COPY
        }
        stage_out.append(new_coor_out)

        if (self.umbrella == True) and (self.us_template != ''):
            out_string = "_%d.out" % (replica.cycle-1)
            rstr_out = {
                'source': (replica.new_restraints + '.out'),
                'target': 'staging:///%s' % (replica_path + replica.new_restraints + out_string),
                'action': rp.COPY
            }
            stage_out.append(rstr_out)
        
        if self.dims[dim_str]['type'] == 'salt':
            info_out = {
                'source': new_info,
                'target': 'staging:///%s' % (replica_path + new_info),
                'action': rp.COPY
            }
            stage_out.append(info_out)

        current_group = []
        for repl in group:
            current_group.append(repl.id)

        #-----------------------------------------------------------------------
        # for all
        if self.nr_dims == 3:
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
                "cycle" : str(replica.cycle),
                "nr_dims": str(self.nr_dims),
                "init_temp": str(self.init_temp)
                }
        elif self.nr_dims == 2:
            data = {
                "p1" : str(replica.dims['d1']['par']),
                "p2" : str(replica.dims['d2']['par']),
                "t1" : str(replica.dims['d1']['type']),
                "t2" : str(replica.dims['d2']['type']),
                "cycle_steps": str(self.cycle_steps),
                "new_restraints" : str(replica.new_restraints),
                "amber_input" : str(self.amber_input),
                "new_input_file" : str(new_input_file),
                "us_template": str(self.us_template),
                "cycle" : str(replica.cycle),
                "nr_dims": str(self.nr_dims),
                "init_temp": str(self.init_temp)
                }
        elif self.nr_dims == 1:
            data = {
                "p1" : str(replica.dims['d1']['par']),
                "t1" : str(replica.dims['d1']['type']),
                "cycle_steps": str(self.cycle_steps),
                "new_restraints" : str(replica.new_restraints),
                "amber_input" : str(self.amber_input),
                "new_input_file" : str(new_input_file),
                "us_template": str(self.us_template),
                "cycle" : str(replica.cycle),
                "nr_dims": str(self.nr_dims),
                "init_temp": str(self.init_temp)
                }

        dump_data = json.dumps(data)
        json_pre_data_bash = dump_data.replace("\\", "")
        json_pre_data_sh   = dump_data.replace("\"", "\\\\\"")

        if self.dims[dim_str]['type'] == 'temperature':

            rstr_vals = []
            for key in replica.dims:
                if replica.dims[key]['type'] == 'umbrella':
                    rstr_vals.append(replica.dims[key]['par'])

            if len(rstr_vals) == 0:
                rstr_vals.append('_')
                rstr_vals.append('_')
            if len(rstr_vals) == 1:
                rstr_vals.append('_')

            data = {
                "rid": str(replica.id),
                "replica_cycle" : str(replica.cycle-1),
                "current_cycle" : str(current_cycle),
                "base_name" : str(basename),
                "replicas" : str(self.replicas),
                "amber_parameters": str(self.amber_parameters),
                "new_restraints" : str(replica.new_restraints),
                "init_temp": str(replica.dims[dim_str]['par']),
                "rstr_vals" : rstr_vals
                }

            dump_data = json.dumps(data)
            json_post_data_bash = dump_data.replace("\\", "")
            json_post_data_sh   = dump_data.replace("\"", "\\\\\"")

        #-----------------------------------------------------------------------
        self.logger.info( "current group: " )
        self.logger.info( current_group )

        if self.dims[dim_str]['type'] == 'umbrella':

            rstr_vals = []
            for key in replica.dims:
                if replica.dims[key]['type'] == 'umbrella':
                    rstr_vals.append(replica.dims[key]['par'])

            if len(rstr_vals) == 0:
                rstr_vals.append('_')
                rstr_vals.append('_')
            if len(rstr_vals) == 1:
                rstr_vals.append('_')

            current_group_rst = {}
            for repl in group:
                current_group_rst[str(repl.id)] = str(repl.new_restraints)
                
            base_restraint = self.us_template + "."

            # if no temperature exchange
            if self.temperature_str == '':
                temp_str = str(self.init_temp)
            else:
                temp_str = str(replica.dims[self.temperature_str]['par'])

            data = {
                "rid": str(rid),
                "replica_cycle" : str(replica.cycle-1),
                "replicas" : str(self.replicas),
                "base_name" : str(basename),
                "init_temp" : temp_str,
                "amber_input" : str(self.amber_input),
                "amber_parameters": str(self.amber_parameters),
                "new_restraints" : str(replica.new_restraints),
                "current_group_rst" : current_group_rst,
                "rstr_vals" : rstr_vals
            }
            dump_data = json.dumps(data)
            json_post_data_bash = dump_data.replace("\\", "")
            json_post_data_sh   = dump_data.replace("\"", "\\\\\"")
        
        if self.dims[dim_str]['type'] == 'salt':
            # 
            current_group_tsu = {}
            for repl in group:
                # if no temperature exchange
                if self.temperature_str == '':
                    temp_str = str(self.init_temp)
                else:
                    temp_str = str(repl.dims[self.temperature_str]['par'])
                current_group_tsu[str(repl.id)] = \
                    [temp_str, \
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
        
        if (self.replica_gpu == True):
            amber_str = self.amber_path_gpu
        elif (self.replica_mpi == True):
            amber_str = self.amber_path_mpi
        else:
            amber_str = self.amber_path
        
        if self.dims[dim_str]['type'] == 'temperature' and self.exchange_mpi == False:
            # matrix_calculator_temp_ex.py
            stage_in.append(sd_shared_list[2])
        if self.dims[dim_str]['type'] == 'umbrella' and self.exchange_mpi == False: 
            # matrix_calculator_us_ex.py
            stage_in.append(sd_shared_list[3])
        
        cu = rp.ComputeUnitDescription()
        cu.cores = self.replica_cores    
        cu.mpi = self.replica_mpi
        
        if KERNELS[self.resource]["shell"] == "bash":
            cu.executable = '/bin/bash'
            pre_exec_str  = "python input_file_builder.py " + "\'" + \
                           json_pre_data_bash + "\'"
            if self.dims[dim_str]['type'] == 'temperature':
                if self.exchange_mpi == False:
                    post_exec_str = "python matrix_calculator_temp_ex.py " + "\'" + \
                                json_post_data_bash + "\'"
                else:
                    post_exec_str = " "
            if self.dims[dim_str]['type'] == 'umbrella':
                post_exec_str = "python matrix_calculator_us_ex.py " + "\'" + \
                                json_post_data_bash + "\'"
        elif KERNELS[self.resource]["shell"] == "bourne":
            cu.executable = '/bin/sh'
            pre_exec_str = "python input_file_builder.py " + "\'" + \
                           json_pre_data_sh + "\'"
            if self.dims[dim_str]['type'] == 'temperature':
                if self.exchange_mpi == False:
                    post_exec_str = "python matrix_calculator_temp_ex.py " + "\'" + \
                                json_post_data_sh + "\'"
                else:
                    post_exec_str = " "
            if self.dims[dim_str]['type'] == 'umbrella':
                post_exec_str = "python matrix_calculator_us_ex.py " + "\'" + \
                                json_post_data_sh + "\'"

        if replica.cycle == 1 or self.restart_done == False:

            if replica.cycle == 1:
                argument_str = " -O " + " -i " + new_input_file + \
                               " -o " + output_file + \
                               " -p " +  self.amber_parameters + \
                               " -c " + replica.coor_file + \
                               " -r " + new_coor + \
                               " -x " + new_traj + \
                               " -inf " + new_info  
            if  self.restart_done == False:
                argument_str = " -O " + " -i " + new_input_file + \
                               " -o " + output_file + \
                               " -p " +  self.amber_parameters + \
                               " -c " + old_coor + \
                               " -r " + new_coor + \
                               " -x " + new_traj + \
                               " -inf " + new_info

            if (self.umbrella == True) and (self.us_template != ''):
                if self.restart_done == False:
                    old_path = self.restart_object.old_sandbox + '/staging_area/' + replica.new_restraints
                    self.logger.info( "restart_path: {0}".format( old_path ) )
                    # restraint file
                    restraints_in_st = {'source': old_path,
                                        'target': replica.new_restraints,
                                        'action': rp.COPY
                    }
                    stage_in.append(restraints_in_st)
                
                restraints_out = replica.new_restraints
                restraints_out_st = {
                    'source': (replica.new_restraints),
                    'target': 'staging:///%s' % (replica.new_restraints),
                    'action': rp.COPY
                }
                stage_out.append(restraints_out_st)

                # restraint template file: ace_ala_nme_us.RST
                stage_in.append(sd_shared_list[8])

            if self.restart_done == False:
                old_path = self.restart_object.old_sandbox + 'staging_area/' + replica_path + old_coor
                old_coor_st = {'source': old_path,
                               'target': (old_coor),
                               'action': rp.COPY
                }
                stage_in.append(old_coor_st)

            #-------------------------------------------------------------------
            # stagein amber_parameters (.param7) and amber_input template (.mdin)  
            # 
            for i in range(2):
                stage_in.append(sd_shared_list[i])
                        
            # replica coor
            repl_coor = replica.coor_file
            # index of replica_coor
            c_index = self.shared_files.index(repl_coor) 
            stage_in.append(sd_shared_list[c_index])
            # input_file_builder.py
            stage_in.append(sd_shared_list[4])

            #-------------------------------------------------------------------
            if (self.replica_mpi == False) and (self.replica_gpu == False):
                cu.pre_exec = self.pre_exec
                if self.dims[dim_str]['type'] != 'salt':
                    cu.arguments = ["-c", pre_exec_str + \
                                    "; wait; " + \
                                    amber_str + \
                                    argument_str + \
                                    "; wait; " + \
                                    post_exec_str]
                else:
                    cu.arguments = ["-c", pre_exec_str + \
                                    "; wait; " + \
                                    amber_str + \
                                    argument_str]
            else:
                cu.executable = amber_str + argument_str
                if self.dims[dim_str]['type'] != 'salt':
                    cu.pre_exec = self.pre_exec + [pre_exec_str]
                    cu.post_exec = [post_exec_str]
                else:
                    cu.pre_exec = self.pre_exec + [pre_exec_str]
            cu.input_staging = stage_in
            cu.output_staging = stage_out

        else:
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
            stage_in.append(sd_shared_list[1])

            # input_file_builder.py
            stage_in.append(sd_shared_list[4])

            if (self.umbrella == True) and (self.us_template != ''):
                # restraint file
                restraints_in_st = {'source': 'staging:///%s' % replica.new_restraints,
                                    'target': replica.new_restraints,
                                    'action': rp.COPY
                }
                stage_in.append(restraints_in_st)
            
            old_coor_st = {'source': 'staging:///%s' % (replica_path + old_coor),
                           'target': (old_coor),
                           'action': rp.LINK
            }
            stage_in.append(old_coor_st)

            #-------------------------------------------------------------------
            new_coor_out = {
                'source': new_coor,
                'target': 'staging:///%s' % (replica_path + new_coor),
                'action': rp.COPY
            }
            stage_out.append(new_coor_out)
               
            if (self.replica_mpi == False) and (self.replica_gpu == False):
                cu.pre_exec = self.pre_exec
                if self.dims[dim_str]['type'] != 'salt':
                    cu.arguments = ["-c", pre_exec_str + \
                                    "; wait; " + \
                                    amber_str + \
                                    argument_str + \
                                    "; wait; " + \
                                    post_exec_str]
                else:
                    cu.arguments = ["-c", pre_exec_str + \
                                    "; wait; " + \
                                    amber_str + \
                                    argument_str]
            else:
                cu.executable = amber_str + argument_str
                if self.dims[dim_str]['type'] != 'salt':
                    cu.pre_exec = self.pre_exec + [pre_exec_str]
                    cu.post_exec = [post_exec_str]
                else:
                    cu.pre_exec = self.pre_exec + [pre_exec_str]
            cu.input_staging = stage_in
            cu.output_staging = stage_out
                
        return cu

    #---------------------------------------------------------------------------
    #                     
    def prepare_group_for_md(self, 
                             current_cycle, 
                             dim_int, 
                             dim_str, 
                             group, 
                             sd_shared_list):

        """Prepares a (single!) RPs compute unit for a given group of replicas 
        to run MD simulation.

        Note: this feature is only available for temperature and umbrella 
        exchange! Feel free to implement this for salt concentration exchange as
        well :-) It was originally designed for multi-dimensional simulations

        Args:
            current_cycle - integer representing number of the current 
            simulation cycle

            dim_int - integer representing the index of the current dimension

            dim_str - string representing the index of the current dimension

            group - list of replica objects which are in the same group in 
            current dimension

            sd_shared_list - list of RPs data directives corresponding to 
            simulation input files

        Returns:
            RPs compute unit
        """


        group_id = group[0].group_idx[dim_int-1]

        stage_out = []
        stage_in  = []

        #-----------------------------------------------------------------------
        # stagein amber_parameters (.param7) and amber_input template (.mdin)
        for i in range(2):
            stage_in.append(sd_shared_list[i])

        # restraint template file: ace_ala_nme_us.RST
        stage_in.append(sd_shared_list[5])

        if (self.dims[dim_str]['type'] == 'temperature') and (self.nr_dims==3):
            # remote_calculator_temp_ex_mpi.py file
            stage_in.append(sd_shared_list[2])
        if (self.dims[dim_str]['type'] == 'umbrella') and (self.nr_dims==3):
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
            new_input_file = "%s_%d_%d.mdin" % (basename, \
                                                replica.id, \
                                                replica.cycle)
            output_file = "%s_%d_%d.mdout" % (self.inp_basename, \
                                              replica.id, \
                                              (replica.cycle))

            replica.new_coor = "%s_%d_%d.rst" % (basename, \
                                                 replica.id, \
                                                 replica.cycle)
            replica.new_traj = "%s_%d_%d.mdcrd" % (basename, \
                                                   replica.id, \
                                                   replica.cycle)
            replica.new_info = "%s_%d_%d.mdinfo" % (basename, \
                                                    replica.id, \
                                                    replica.cycle)

            new_coor = replica.new_coor
            new_traj = replica.new_traj
            new_info = replica.new_info

            replica.old_coor = "%s_%d_%d.rst" % (basename, \
                                                 replica.id, \
                                                 (replica.cycle-1))
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
                    'action':   rp.TRANSFER
                }
                stage_out.append(info_local)

            if self.down_mdout == True:
                output_local = {
                    'source':   output_file,
                    'target':   output_file,
                    'action':   rp.TRANSFER
                }
                stage_out.append(output_local)

            replica_path = "replica_%d/" % (rid)

            new_coor_out = {
                'source': new_coor,
                'target': 'staging:///%s' % (replica_path + new_coor),
                'action': rp.COPY
            }
            stage_out.append(new_coor_out)

            if self.us_template != '':
                out_string = "_%d.out" % (replica.cycle)
                rstr_out = {
                    'source': (replica.new_restraints + '.out'),
                    'target': 'staging:///%s' % (replica_path + \
                                                 replica.new_restraints + \
                                                 out_string),
                    'action': rp.COPY
                }
                stage_out.append(rstr_out)
            
            matrix_col = "matrix_column_%s_%s.dat" % (str(group_id), \
                                                      str(replica.cycle))
            matrix_col_out = {
                'source': matrix_col,
                'target': 'staging:///%s' % (matrix_col),
                'action': rp.COPY
            }
            stage_out.append(matrix_col_out)

            if self.copy_mdinfo == True:
                info_out = {
                    'source': new_info,
                    'target': 'staging:///%s' % (replica_path + new_info),
                    'action': rp.COPY
                }
                stage_out.append(info_out)

            #-------------------------------------------------------------------
            
            data['ex'][str(rid)] = {}
            if (dim_str == 'd1'):
                cd_str = "1"
            if (dim_str == 'd2'):
                cd_str = "2"
            if (dim_str == 'd3'):
                cd_str = "3"
               
            if self.nr_dims == 3:
                data['ex'][str(rid)] = {
                    "cd" : cd_str,
                    "p1" : str(replica.dims['d1']['par']),
                    "p2" : str(replica.dims['d2']['par']),
                    "p3" : str(replica.dims['d3']['par']),
                    "t1" : str(replica.dims['d1']['type']),
                    "t2" : str(replica.dims['d2']['type']),
                    "t3" : str(replica.dims['d3']['type']),
                    "new_rstr" : str(replica.new_restraints[len_substr:]),
                    "r_coor" : str(replica.coor_file[len_substr:])
                    }
            elif self.nr_dims == 2:
                data['ex'][str(rid)] = {
                    "cd" : cd_str,
                    "p1" : str(replica.dims['d1']['par']),
                    "p2" : str(replica.dims['d2']['par']),
                    "t1" : str(replica.dims['d1']['type']),
                    "t2" : str(replica.dims['d2']['type']),
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
                    'action': rp.COPY
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
                                    'action': rp.COPY
                }
                stage_in.append(restraints_in_st)

                old_coor_st = {'source': 'staging:///%s' % (replica_path + old_coor),
                               'target': (old_coor),
                               'action': rp.LINK
                }
                stage_in.append(old_coor_st)

            replica.cycle += 1
        #-----------------------------------------------------------------------
        # data for input file generation 
        dump_data = json.dumps(data)
        json_data_bash = dump_data.replace("\\", "")
        json_data_sh   = dump_data.replace("\"", "\\\\\"")

        cu = rp.ComputeUnitDescription()

        if (self.dims[dim_str]['type'] == 'umbrella'):
            if KERNELS[self.resource]["shell"] == "bash":
                exec_str = "python matrix_calculator_us_ex_mpi.py "
                cu.executable = exec_str + "\'" + json_data_bash + "\'"
            elif KERNELS[self.resource]["shell"] == "bourne":
                cu.executable = exec_str + "\'" + json_data_sh + "\'"

        if (self.dims[dim_str]['type'] == 'temperature'):
            exec_str = "python matrix_calculator_temp_ex_mpi.py "
            if KERNELS[self.resource]["shell"] == "bash":
                cu.executable = exec_str + "\'" + json_data_bash + "\'"
            elif KERNELS[self.resource]["shell"] == "bourne":
                cu.executable = exec_str + "\'" + json_data_sh + "\'"

        cu.pre_exec = self.pre_exec
        cu.input_staging = stage_in
        cu.output_staging = stage_out
        cu.cores = len(group)
        cu.mpi = True

        return cu

    #---------------------------------------------------------------------------
    #
    def prepare_replica_for_exchange(self, 
                                     current_cycle,
                                     dim_int, 
                                     dim_str, 
                                     group, 
                                     replica, 
                                     sd_shared_list):
    
        """Prepares RPs compute unit for a given replica to perform exchange 
        calculations on remote HPC cluster.

        Note: this function should be called for salt concentration exchange 
        only! 

        Args:
            current_cycle - integer representing number of the current 
            simulation cycle

            dim_int - integer representing the index of the current dimension

            dim_str - string representing the index of the current dimension

            group - list of replica objects which are in the same group with 
            a given replica in current dimension

            replica - replica object for which we are preparing RPs compute unit

            sd_shared_list - list of RPs data directives corresponding to 
            simulation input files

        Returns:
            RPs compute unit
        """

        basename = self.inp_basename
        matrix_col = "matrix_column_%s_%s.dat" % (str(replica.id), \
                                                  str(replica.cycle-1))

        current_group = []
        for repl in group:
            current_group.append( repl.id )
        
        cu = rp.ComputeUnitDescription()
        
        current_group_tsu = {}
        for repl in group:
            # no temperature exchange
            if self.temperature_str == '':
                temp_str = str(self.init_temp)
            else:
                temp_str = str(repl.dims[self.temperature_str]['par'])
            current_group_tsu[str(repl.id)] = \
                [temp_str, \
                str(repl.dims[dim_str]['par']), \
                str(repl.new_restraints)]

        # no temperature exchange
        if self.temperature_str == '':
            temp_str = str(self.init_temp)
        else:
            temp_str = str(replica.dims[self.temperature_str]['par'])
        data = {
            "rid": str(replica.id),
            "replica_cycle" : str(replica.cycle-1),
            "replicas" : str(self.replicas),
            "base_name" : str(basename),
            "init_temp" : temp_str,
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

        salt_pre_exec = ["python salt_conc_pre_exec.py " + \
                         "\'" + \
                         json_data + "\'"]
        cu.pre_exec = self.pre_exec + salt_pre_exec
        cu.executable = self.amber_path_mpi
        salt_post_exec = ["python salt_conc_post_exec.py " + \
                          "\'" + \
                          json_data + "\'"]
        cu.post_exec = salt_post_exec

        rid = replica.id
        in_list = []
        in_list.append(sd_shared_list[0])
        in_list.append(sd_shared_list[1])
        in_list.append(sd_shared_list[9])
        in_list.append(sd_shared_list[10])

        if (self.umbrella == True) and (self.us_template != ''):
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
                    'action': rp.COPY
                }
                in_list.append(rstr_in)
  
        out_list = []
        matrix_col_out = {
            'source': matrix_col,
            'target': 'staging:///%s' % (matrix_col),
            'action': rp.COPY
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
    def prepare_global_ex_calc(self, 
                               current_cycle, 
                               dim_int, 
                               dim_str, 
                               replicas, 
                               sd_shared_list):

        """Prepares RPs compute unit for the final stage of exchange procedure.
        If we perform MPI exchange for temperature exchange 
        global_ex_calculator_tex_mpi.py RAM is used.
        If we perform MPI exchange for umbrella exchange 
        global_ex_calculator_us_mpi.py RAM is used.
        If we perform group execution (for MD) for temperature/umbrella exchange
        global_ex_calculator_gr.py is used
        If we perform exchange for salt concentration exchange
        global_ex_calculator.py is used
        If MD tasks are generated for each replica individually and we perform
        temperature exchange global_ex_calculator_temp_ex.py
        If MD tasks are generated for each replica individually and we perform
        umbrella exchange global_ex_calculator_us_ex.py

        Args:
            current_cycle - integer representing number of the current 
            simulation cycle

            dim_int - integer representing the index of the current dimension

            dim_str - string representing the index of the current dimension

            replicas - list of replica objects for which we are finalizing 
            exchange procedure

            sd_shared_list - list of RPs data directives corresponding to 
            simulation input files

        Returns:
            RPs compute unit
        """

        stage_out = []
        stage_in = []

        if self.nr_dims == 3:
            d1_type = self.dims['d1']['type']
            d2_type = self.dims['d2']['type']
            d3_type = self.dims['d3']['type']
            dims_string = d1_type + ' ' + d2_type + ' ' + d3_type
        elif self.nr_dims == 2:
            d1_type = self.dims['d1']['type']
            d2_type = self.dims['d2']['type']
            dims_string = d1_type + ' ' + d2_type
        elif self.nr_dims == 1:
            d1_type = self.dims['d1']['type']
            dims_string = d1_type

        group_nr = self.groups_numbers[dim_int-1]
        cycle = replicas[0].cycle-1

        group_ids = self.get_all_groups_ids(dim_int, replicas)

        data = {"replicas" : str(self.replicas),
                "current_cycle" : str(current_cycle),
                "cycle" : str(cycle),
                "dimension" : str(dim_int),
                "group_nr" : str(group_nr),
                "group_ids" : group_ids,
                "dim_string": dims_string
        }
        dump_data = json.dumps(data)
        json_data_single = dump_data.replace("\\", "")
        
        if self.group_exec == True:
            # global_ex_calculator_gr.py file
            stage_in.append(sd_shared_list[4])
        elif self.exchange_mpi == False:
            if (self.dims[dim_str]['type'] == 'temperature'): 
                # global_ex_calculator_temp_ex.py file
                stage_in.append(sd_shared_list[6])
            if (self.dims[dim_str]['type'] == 'umbrella'):
                # global_ex_calculator_us_ex.py file
                stage_in.append(sd_shared_list[7])
            if (self.dims[dim_str]['type'] == 'salt'):
                # global_ex_calculator.py file
                stage_in.append(sd_shared_list[5])

        outfile = "pairs_for_exchange_{dim}_{cycle}.dat".format(dim=dim_int, \
                                                                cycle=current_cycle)
        stage_out.append(outfile)

        cu = rp.ComputeUnitDescription()

        if (self.exchange_mpi == True): 
            if (self.dims[dim_str]['type'] == 'temperature'):
                # global_ex_calculator_tex_mpi.py file
                stage_in.append(sd_shared_list[2])

                cu.pre_exec = self.pre_exec
                cu.executable = "python"
                cu.input_staging  = stage_in
                cu.arguments = ["global_ex_calculator_tex_mpi.py", \
                                 str(cycle), \
                                 str(self.replicas), \
                                 str(self.inp_basename)]

                if self.cores < self.replicas:
                    if self.exchange_mpi_cores != 0:
                        if self.replicas % self.exchange_mpi_cores == 0:
                            cu.cores = self.exchange_mpi_cores
                    elif (self.replicas % self.cores) == 0:
                        cu.cores = self.cores
                    else:
                        self.logger.info("Number of replicas must be divisible by the number of Pilot cores!")
                        self.logger.info("pilot cores: {0}; replicas {1}".format(self.cores, self.replicas))
                        sys.exit()
        
                elif self.cores >= self.replicas:
                    cu.cores = self.replicas
                else:
                    self.logger.info("Number of replicas must be divisible by the number of Pilot cores!")
                    self.logger.info("pilot cores: {0}; replicas {1}".format(self.cores, self.replicas))
                    sys.exit()
                
                cu.mpi = True         
                cu.output_staging = stage_out

            elif (self.dims[dim_str]['type'] == 'umbrella'):
                all_restraints = {}
                all_temperatures = {}
                for repl in replicas:
                    all_restraints[str(repl.id)] = str(repl.new_restraints)
                    all_temperatures[str(repl.id)] = str(repl.new_temperature)

                data = {
                    "current_cycle" : str(current_cycle),
                    "replicas" : str(self.replicas),
                    "base_name" : str(self.inp_basename),
                    "all_temperatures" : all_temperatures,
                    "all_restraints" : all_restraints
                }
                dump_data = json.dumps(data)
                json_data_us = dump_data.replace("\\", "")

                # global_ex_calculator_us_mpi.py file
                stage_in.append(sd_shared_list[3])

                cu.pre_exec = self.pre_exec
                cu.executable = "python"
                cu.input_staging  = stage_in
                cu.arguments = ["global_ex_calculator_us_mpi.py", json_data_us]

                if self.cores < self.replicas:
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
            if (self.dims[dim_str]['type'] == 'temperature'):
                cu.pre_exec = self.pre_exec
                cu.executable = "python"
                cu.input_staging  = stage_in
                if self.group_exec == True:
                    cu.arguments = ["global_ex_calculator_gr.py", json_data_single]            
                else:
                    cu.arguments = ["global_ex_calculator_temp_ex.py", json_data_single]                 
                cu.cores = 1
                cu.mpi = False            
                cu.output_staging = stage_out

            elif (self.dims[dim_str]['type'] == 'umbrella'):
                cu.pre_exec = self.pre_exec
                cu.executable = "python"
                cu.input_staging  = stage_in
                if self.group_exec == True:
                    cu.arguments = ["global_ex_calculator_gr.py", json_data_single]            
                else:
                    cu.arguments = ["global_ex_calculator_us_ex.py", json_data_single]                 
                cu.cores = 1
                cu.mpi = False            
                cu.output_staging = stage_out
            else:
                cu.pre_exec = self.pre_exec
                cu.executable = "python"
                cu.input_staging  = stage_in
                if self.group_exec == True:
                    cu.arguments = ["global_ex_calculator_gr.py", json_data_single]            
                else:
                    cu.arguments = ["global_ex_calculator.py", json_data_single]                 
                cu.cores = 1
                cu.mpi = False            
                cu.output_staging = stage_out

        return cu

    #---------------------------------------------------------------------------
    #
    def exchange_params(self, dim_str, replica_1, replica_2):
        """Exchanges parameters of the two given replicas in the given 
        dimension. 

        Args:
            dim_str - string representing the index of the current dimension

            replica_1 - replica object for which is exchange parameter

            replica_2 - replica object for which is exchange parameter

        Returns:
            None
        """

        if (self.dims[dim_str]['type'] == 'umbrella'):
            rstr = replica_2.dims[dim_str]['par']
            replica_2.dims[dim_str]['par'] = replica_1.dims[dim_str]['par']
            replica_1.dims[dim_str]['par'] = rstr
            
            rstr = replica_2.new_restraints
            replica_2.new_restraints = replica_1.new_restraints
            replica_1.new_restraints = rstr
        else:
            temp = replica_2.dims[dim_str]['par']
            replica_2.dims[dim_str]['par'] = replica_1.dims[dim_str]['par']
            replica_1.dims[dim_str]['par'] = temp

        # exchange group indexes
        dim_int = int(dim_str[1])-1
        for i,j in enumerate(replica_1.group_idx):
            if (i != dim_int):
                tmp = replica_1.group_idx[i]
                replica_1.group_idx[i] = replica_2.group_idx[i]
                replica_2.group_idx[i] = tmp

    #---------------------------------------------------------------------------
    #
    def do_exchange(self, current_cycle, dim_int, dim_str, replicas):

        """Reads pairs_for_exchange_d_c.dat file to determine which replicas
        should exchange parameters. Calls exchange_params() method to exchange
        parameters for a pair of replicas. Updates new_sandbox attribute of the
        restart_object.

        Args:
            current_cycle - integer representing number of the current 
            simulation cycle

            dim_int - integer representing the index of the current dimension

            dim_str - string representing the index of the current dimension

            replicas - list of replica objects

        Returns:
            None
        """

        r1 = None
        r2 = None

        infile = "pairs_for_exchange_{dim}_{cycle}.dat".format(dim=dim_int, \
                                                               cycle=current_cycle)
        try:
            f = open(infile)
            lines = f.readlines()
            f.close()
            for l in lines:
                pair = l.split()
                if pair[0].isdigit() and pair[1].isdigit():
                    r1_id = int(pair[0])
                    r2_id = int(pair[1])
                    for r in replicas:
                        if r.id == r1_id:
                            r1 = r
                        if r.id == r2_id:
                            r2 = r
                    #-----------------------------------------------------------
                    # swap parameters
                    if r1 is not None and r2 is not None and self.exchange_off[dim_int-1] == False:
                        self.exchange_params(dim_str, r1, r2)
                        r1.swap = 1
                        r2.swap = 1
                else:
                    i = l[-1]
                    while i != '/':
                        l = l[:-1]
                        i = l[-1]
                    self.restart_object.new_sandbox = l
        except:
            raise

    #---------------------------------------------------------------------------
    #
    def get_current_group_ids(self, dim_int, replicas, replica):

        """Retrieves ids of replicas, which are in the same group with a given
        replica

        Args:
            dim_int - integer representing the index of the current dimension

            replicas - list of replica objects

            replica - replica object for which we determine ids of it's group
            members  

        Returns:
            current_group - list with ids of replicas, which are in the same 
            group with a given replica
        """

        current_group = []

        if self.nr_dims == 3:
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
        elif self.nr_dims == 2:
            for r1 in replicas:
                if dim_int == 1:
                    r1_par = r1.dims['d2']['par']
                    my_par = replica.dims['d2']['par'] 
                    if r1_par == my_par:
                        current_group.append(str(r1.id))

                elif dim_int == 2:
                    r1_par = r1.dims['d1']['par']
                    my_par = replica.dims['d1']['par']
                    if r1_par == my_par:
                        current_group.append(str(r1.id))

        return current_group

    #---------------------------------------------------------------------------
    #
    def get_all_groups_ids(self, dim_int, replicas):

        """Composes a 2d list of replica ids, which are grouped based on their
        group index in the current dimension

        Args:
            dim_int - integer representing the index of the current dimension

            replicas - list of replica objects 

        Returns:
            all_groups - 2d list with ids of replicas, which are grouped 
            together based on their group index in the current dimension 
        """

        dim = dim_int-1

        all_groups = []
        for i in range(self.groups_numbers[dim]):
            all_groups.append([None])
        for r in replicas:
            all_groups[r.group_idx[dim]].append(r.id)

        self.logger.info("all groups ids before: {0}".format( all_groups ) )

        for gr in all_groups:
            gr.pop(0) 

        for i,v in enumerate(all_groups):
            if len(all_groups[i]) == 0:
                all_groups.pop(i)

        self.logger.info("all groups ids after: {0}".format( all_groups ) )

        return all_groups

    #---------------------------------------------------------------------------
    #
    def get_all_groups(self, dim_int, replicas):

        """Composes a 2d list of replicas, which are grouped based on their
        group index in the current dimension

        Args:
            dim_int - integer representing the index of the current dimension

            replicas - list of replica objects 

        Returns:
            all_groups - 2d list of replicas, which are grouped together based 
            on their group index in the current dimension 
        """

        dim = dim_int-1

        all_groups = []
        for i in range(self.groups_numbers[dim]):
            all_groups.append([None])
        for r in replicas:
            all_groups[r.group_idx[dim]].append(r)

        return all_groups

    #---------------------------------------------------------------------------
    #
    def get_replica_group(self, dim_int, replicas, replica):

        """Composes a 2d list of replicas, which are grouped based on their
        group index in the current dimension

        Args:
            dim_int - integer representing the index of the current dimension

            replicas - list of replica objects 

            replica - replica object for which we are determining group members 

        Returns:
            group - list of replica objects, which are in the same group as a 
            given replica 
        """

        dim = dim_int-1
        group = list()

        for r in replicas:
            if r.group_idx[dim] == replica.group_idx[dim]:
                group.append(r)

        return group

    #---------------------------------------------------------------------------
    #
    def init_matrices(self, replicas):

        """initializes a 2d lists with ids of replicas to track accepted and
        attempted exchanges

        Args:
            replicas - list of replica objects

        Returns:
            None  
        """

        # TODO
        pass

