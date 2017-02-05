"""
.. module:: radical.repex.application_management_modules.amm_namd
.. moduleauthor::  <antons.treikalis@gmail.com>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import json
import shutil
import pickle
import tarfile
from os import path
import radical.pilot as rp
import radical.utils.logger as rul
from kernels.kernels import KERNELS
import ram_namd.input_file_builder
from replicas.replica import Replica
from repex_utils.simulation_restart import Restart

#-------------------------------------------------------------------------------

class AmmNamd(object):
    """Application management Module (AMM) for NAMD kernel. For each simulation 
    should be created only a single instance of AMM. 

    Attributes:
        Way too many
    """

    def __init__(self, inp_file, rconfig,  work_dir_local):
        """
        Args:
            inp_file - simulation input file with parameters specified by user 
            rconfig - resource configuration file
            work_dir_local - directory from which main simulation script was invoked
        """

        self.name = 'AmmNAMD.log'
        self.ex_name = 'temperature'
        self.logger  = rul.get_logger ('radical.repex', self.name)
        
        self.namd_structure   = inp_file['remd.input'].get('namd_structure')
        self.namd_coordinates = inp_file['remd.input'].get('namd_coordinates')
        self.namd_parameters  = inp_file['remd.input'].get('namd_parameters')
 
        self.resource      = rconfig.get('resource')
        self.cores         = int(rconfig.get('cores', '1'))
        self.cycle_steps   = int(inp_file['remd.input'].get('steps_per_cycle'))
        self.nr_cycles     = int(inp_file['remd.input'].get('number_of_cycles','1'))
        self.replica_cores = int(inp_file['remd.input'].get('replica_cores', '1'))

        # hardcoded for 1d
        self.nr_dims = 1
        self.groups_numbers = [1]

        self.dims = {}
        self.dims['d1'] = {'replicas' : None, 'type' : None} 

        if inp_file['dim.input'].get('d1'):
            self.dims['d1']['replicas'] = int(inp_file['dim.input']\
                               ['d1'].get("number_of_replicas"))
            self.dims['d1']['type'] = (inp_file['dim.input']['d1'].get("type"))

        self.replicas = int(inp_file['dim.input']['d1'].get("number_of_replicas"))

        # for restart
        self.restart           = inp_file['remd.input'].get('restart', 'False')
        self.restart_file      = inp_file['remd.input'].get('restart_file', '')
        if self.restart == 'True':
            self.restart = True
            self.restart_done = False
        else:
            self.restart = False
            self.restart_done = True

        if inp_file['remd.input'].get('exchange_mpi') == "True":
            self.exchange_mpi = True
        else:
            self.exchange_mpi = False

        self.min_temp = float(inp_file['dim.input']['d1'].get('min_temperature'))
        self.max_temp = float(inp_file['dim.input']['d1'].get('max_temperature'))
        self.work_dir_local    = work_dir_local
        self.current_cycle     = -1
        self.input_folder      = inp_file['remd.input'].get('input_folder')

        self.pre_exec  = KERNELS[self.resource]["kernels"]["namd"]["pre_execution"]
        self.inp_basename = inp_file['remd.input']['input_file_basename']

        self.namd_path = inp_file['remd.input'].get('namd_path')
        if self.namd_path == None:
            self.logger.info("Using default NAMD path for: {0}".format(rconfig.get('resource')))
            self.namd_path = KERNELS[self.resource]["kernels"]["namd"].get("executable")
        if self.namd_path == None:
            self.logger.info("NAMD path can't be found!")
            sys.exit(1)

        self.exchange_off = []
        if (inp_file['dim.input']['d1'].get("exchange_off", "False")) == "True":
            self.exchange_off.append(True)
        else:
            self.exchange_off.append(False)
        
        self.all_temp_list = []

        self.shared_urls = []
        self.shared_files = []

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
 
        structure_path = self.work_dir_local + "/" + self.input_folder + "/" + self.namd_structure
        coords_path = self.work_dir_local + "/" + self.input_folder + "/" + self.namd_coordinates
        params_path = self.work_dir_local + "/" + self.input_folder + "/" + self.namd_parameters

        input_template = self.inp_basename + ".namd"
        input_template_path = self.work_dir_local + "/" + self.input_folder + "/" + input_template

        rams_path = os.path.dirname(ram_namd.input_file_builder.__file__)

        build_inp_path     = rams_path + "/input_file_builder.py"
        global_calc_path   = rams_path + "/global_ex_calculator_mpi.py"
        global_calc_path_s = rams_path + "/global_ex_calculator.py"
        ind_calc_path      = rams_path + "/ind_ex_calculator.py"

        #-----------------------------------------------------------------------

        self.shared_files.append(self.namd_structure)
        self.shared_files.append(self.namd_coordinates)
        self.shared_files.append(self.namd_parameters)
        self.shared_files.append(input_template)
        self.shared_files.append("input_file_builder.py")
        self.shared_files.append("global_ex_calculator_mpi.py")
        self.shared_files.append("global_ex_calculator.py")
        self.shared_files.append("ind_ex_calculator.py")

        #-----------------------------------------------------------------------

        struct_url = 'file://%s' % (structure_path)
        self.shared_urls.append(struct_url)
 
        coords_url = 'file://%s' % (coords_path)
        self.shared_urls.append(coords_url)     

        params_url = 'file://%s' % (params_path)
        self.shared_urls.append(params_url)

        input_url = 'file://%s' % (input_template_path)
        self.shared_urls.append(input_url)

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
        """Initializes replicas with parameters specified in simulation input
        file. Assigns group index in each dimension for each initialized 
        replica. Initializes a restart object of this application management 
        module.  

        Args:
            None

        Returns:
            list of replica objects
        """

        self.restart_object = Restart()
        
        replicas = []
        N = self.replicas
        factor = (self.max_temp/self.min_temp)**(1./(N-1))
        for k in range(N):
            new_temp = self.min_temp * (factor**k)
            r = Replica(k, d1_param=new_temp)
            replicas.append(r)

        # hardcoded for 1d
        for r in replicas:
            r.group_idx[0] = 0

        self.groups_numbers = [1] 
        self.restart_object.groups_numbers = self.groups_numbers
            
        return replicas

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
        
        basename = self.inp_basename
        template = self.inp_basename + ".namd"
            
        outputname = "%s_%d_%d" % (basename, replica.id, replica.cycle)
        replica.new_coor = outputname + ".coor"
        replica.new_vel = outputname + ".vel"
        replica.new_history = outputname + ".history"
        replica.new_ext_system = outputname + ".xsc" 

        old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1))
        old_coor = old_name + ".coor"
        old_vel = old_name + ".vel"
        old_ext_system = old_name + ".xsc"  

        #-----------------------------------------------------------------------

        input_file = "%s_%d_%d.namd" % (self.inp_basename, replica.id, (replica.cycle))

        new_coor = replica.new_coor
        new_vel = replica.new_vel
        new_history = replica.new_history
        new_ext_system = replica.new_ext_system

        stage_out = []
        stage_in = []
 
        history_out = {
            'source': new_history,
            'target': 'staging:///%s' % new_history,
            'action': rp.COPY
        }
        stage_out.append(history_out)
        
        coor_out = {
            'source': new_coor,
            'target': 'staging:///%s' % new_coor,
            'action': rp.COPY
        }                   
        stage_out.append(coor_out)        

        vel_out = {
            'source': new_vel,
            'target': 'staging:///%s' % new_vel,
            'action': rp.COPY
        }
        stage_out.append(vel_out)
        
        ext_out = {
            'source': new_ext_system,
            'target': 'staging:///%s' % new_ext_system,
            'action': rp.COPY
        }
        stage_out.append(ext_out)

        data = {
            "inp_basename": str(self.inp_basename),
            "replica_id": str(replica.id),
            "replica_cycle": str(replica.cycle),
            "cycle_steps": str(self.cycle_steps),
            "namd_structure": str(self.namd_structure),
            "namd_coordinates": str(self.namd_coordinates),
            "namd_parameters": str(self.namd_parameters),
            "swap": str(replica.swap),
            "old_temperature": str(replica.dims['d1']['old_par']),
            "new_temperature": str(replica.dims['d1']['par']),
            }
        dump_pre_data = json.dumps(data)
        json_pre_data = dump_pre_data.replace("\\", "")

        pre_exec_str = "python input_file_builder.py " + "\'" + json_pre_data + "\'"

        cu = rp.ComputeUnitDescription()

        if self.exchange_mpi == True:
            for i in range(5):
                stage_in.append(sd_shared_list[i])

            cu.pre_exec       = self.pre_exec + [pre_exec_str]
            cu.executable     = self.namd_path
            cu.arguments      = [input_file]
            cu.cores          = self.replica_cores
            cu.mpi            = False
            cu.input_staging  = stage_in
            cu.output_staging = stage_out
            
        else:
            for i in range(5):
                stage_in.append(sd_shared_list[i])
            stage_in.append(sd_shared_list[7])

            matrix_col = "matrix_column_%s_%s.dat" % (str(replica.id), 
                                                      str(replica.cycle))
            matrix_col_out = {
                'source': matrix_col,
                'target': 'staging:///%s' % (matrix_col),
                'action': rp.COPY
            }
            stage_out.append(matrix_col_out)

            temperatures = ""
            for r in group:
                temperatures += " " + str(r.dims['d1']['par'])

            data = {
                "replica_id" : str(replica.id),
                "replica_cycle": str(replica.cycle),
                "replicas": str(self.replicas),
                "basename": str(basename),
                "temperatures": temperatures
            }

            dump_post_data = json.dumps(data)
            json_post_data = dump_post_data.replace("\\", "")

            post_exec_str = "python ind_ex_calculator.py " + "\'" + json_post_data + "\'"

            cu.pre_exec       = self.pre_exec  + [pre_exec_str]
            cu.post_exec      = [post_exec_str]
            cu.executable     = self.namd_path
            cu.arguments      = [input_file]
            cu.cores          = self.replica_cores
            cu.mpi            = False
            cu.input_staging  = stage_in
            cu.output_staging = stage_out

        replica.cycle += 1

        return cu
       
    #---------------------------------------------------------------------------
    #
    def prepare_global_ex_calc(self, 
                               current_cycle, 
                               dim_int, 
                               dim_str, 
                               replicas, 
                               sd_shared_list):

        """Prepares RPs compute unit for the exchange procedure.

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

        temperatures = ""
        for r in replicas:
            temperatures += " " + str(r.dims['d1']['par'])

        stage_out = []
        stage_in = []
        cycle = replicas[0].cycle-1

        outfile = "pairs_for_exchange_{cycle}.dat".format(cycle=cycle)
        stage_out.append(outfile)

        if self.exchange_mpi == True:
            # global_ex_calculator_mpi.py file
            stage_in.append(sd_shared_list[5])

            cu = rp.ComputeUnitDescription()
            cu.pre_exec = self.pre_exec
            cu.executable = "python"
            cu.input_staging  = stage_in
            cu.arguments = ["global_ex_calculator_mpi.py", 
                            str(cycle), 
                            str(self.replicas), 
                            str(self.inp_basename),
                            temperatures]

            # tmp guard for supermic
            if self.replicas == 1000:
                cu.cores = self.replicas / 2
            elif self.replicas == 1728:
                cu.cores = self.replicas / 4
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
            # global_ex_calculator.py file
            stage_in.append(sd_shared_list[6])

            cu = rp.ComputeUnitDescription()
            cu.pre_exec = self.pre_exec
            cu.executable = "python"
            cu.input_staging  = stage_in
            cu.arguments = ["global_ex_calculator.py", 
                            str(cycle), 
                            str(self.replicas), 
                            str(self.inp_basename)]
            cu.cores = 1
            cu.mpi = False         
            cu.output_staging = stage_out

        return cu

    #---------------------------------------------------------------------------
    #
    def exchange_params(self, replica_i, replica_j):
        """Performs an exchange of temperatures

        Args:
            replica_i - a replica object
            replica_j - a replica object

        Returns:
            None
        """
        # update old temperature
        replica_i.dims['d1']['old_par'] = replica_i.dims['d1']['par']
        replica_j.dims['d1']['old_par'] = replica_j.dims['d1']['par']

        # swap temperatures
        temperature = replica_j.dims['d1']['par']
        replica_j.dims['d1']['par'] = replica_i.dims['d1']['par']
        replica_i.dims['d1']['par'] = temperature
        # record that swap was performed
        replica_i.swap = 1
        replica_j.swap = 1

    #---------------------------------------------------------------------------
    #
    def do_exchange(self, current_cycle, dim_int, dim_str, replicas):

        """Reads pairs_for_exchange_c.dat file to determine which replicas
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

        cycle = replicas[0].cycle-1

        infile = "pairs_for_exchange_{cycle}.dat".format(cycle=cycle)
        
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
                    if r1 is not None and r2 is not None and self.exchange_off[0] == False:
                        self.exchange_params(r1, r2)
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
