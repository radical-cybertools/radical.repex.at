"""
.. module:: radical.repex.md_kernles.amber_kernels_3d_tsu.kernel_pattern_b_3d_tsu
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
from replicas.replica import Replica2d
from md_kernels.md_kernel_3d_tsu import *
import amber_kernels_3d_tsu.matrix_calculator_temp_ex
import amber_kernels_3d_tsu.matrix_calculator_us_ex
import amber_kernels_3d_tsu.salt_conc_pre_exec
import amber_kernels_3d_tsu.salt_conc_post_exec

#-------------------------------------------------------------------------------------------------------

class AmberKernelPatternB3dTSU(MdKernel3dTSU):
    """This class is responsible for performing all operations related to Amber for RE scheme S2.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.
    """
    def __init__(self, inp_file,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        MdKernel3dTSU.__init__(self, inp_file, work_dir_local)

        self.name = 'ak-patternB-3d-TSU'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        self.pre_exec = KERNELS[self.resource]["kernels"]["amber"]["pre_execution"]
        try:
            self.amber_path = inp_file['input.MD']['amber_path']
        except:
            self.logger.info("Using default Amber path for: {0}".format(inp_file['input.PILOT']['resource']) )
            try:
                self.amber_path = KERNELS[self.resource]["kernels"]["amber"]["executable"]
            except:
                self.logger.info("Amber path for localhost is not defined!")

        self.amber_path_mpi = KERNELS[self.resource]["kernels"]["amber"]["executable_mpi"]

        ########################
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

    #---------------------------------------------------------------------
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


    #----------------------------------------------------------------------------------------------
    # 
    def initialize_replicas(self):
        """Initializes replicas and their attributes to default values
        """

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
                 
                    #---------------------------
                    rid = k + j*self.replicas_d3 + i*self.replicas_d3*self.replicas_d2
                    r1 = self.restraints_files[rid]

                    spacing = (self.us_end_param - self.us_start_param) / float(self.replicas_d3)
                    starting_value = self.us_start_param + k*spacing
                    rstr_val_1 = str(starting_value+spacing)

                    #print "rid: %d temp: %f salt: %f us: %f " % (rid, t1, float(s1), float(rstr_val_1))

                    r = Replica3d(rid, new_temperature=t1, new_salt=s1, new_restraints=r1, rstr_val_1=float(rstr_val_1), cores=1)
                    replicas.append(r)

        return replicas

    # --------------------------------------------------------------------------------------------
    #
    def prepare_shared_data(self):

        parm_path = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_parameters
        coor_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_coordinates
        inp_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_input

        calc_temp = os.path.dirname(amber_kernels_3d_tsu.matrix_calculator_temp_ex.__file__)
        calc_temp_path = calc_temp + "/matrix_calculator_temp_ex.py"

        calc_us = os.path.dirname(amber_kernels_3d_tsu.matrix_calculator_us_ex.__file__)
        calc_us_path = calc_us + "/matrix_calculator_us_ex.py"
   
        salt_pre_exec  = os.path.dirname(amber_kernels_3d_tsu.salt_conc_pre_exec.__file__)
        salt_pre_exec_path = salt_pre_exec + "/salt_conc_pre_exec.py"

        salt_post_exec  = os.path.dirname(amber_kernels_3d_tsu.salt_conc_post_exec.__file__)
        salt_post_exec_path = salt_post_exec + "/salt_conc_post_exec.py"

        rstr_list = []
        for rstr in self.restraints_files:
            rstr_list.append(self.work_dir_local + "/" + rstr)

        #------------------------------------------------
        self.shared_files.append(self.amber_parameters)
        self.shared_files.append(self.amber_coordinates)
        self.shared_files.append(self.amber_input)
        self.shared_files.append("matrix_calculator_temp_ex.py")
        self.shared_files.append("matrix_calculator_us_ex.py")
        self.shared_files.append("salt_conc_pre_exec.py")
        self.shared_files.append("salt_conc_post_exec.py")

        for rstr in self.restraints_files:
            self.shared_files.append(rstr)
        #------------------------------------------------

        parm_url = 'file://%s' % (parm_path)
        self.shared_urls.append(parm_url)

        coor_url = 'file://%s' % (coor_path)
        self.shared_urls.append(coor_url)

        inp_url = 'file://%s' % (inp_path)
        self.shared_urls.append(inp_url)

        calc_temp_url = 'file://%s' % (calc_temp_path)
        self.shared_urls.append(calc_temp_url)

        calc_us_url = 'file://%s' % (calc_us_path)
        self.shared_urls.append(calc_us_url)

        salt_pre_exec_url = 'file://%s' % (salt_pre_exec_path)
        self.shared_urls.append(salt_pre_exec_url)

        salt_post_exec_url = 'file://%s' % (salt_post_exec_path)
        self.shared_urls.append(salt_post_exec_url)

        for rstr_p in rstr_list:
            rstr_url = 'file://%s' % (rstr_p)
            self.shared_urls.append(rstr_url)
 
    #---------------------------------------------------------------------------------------------
    #  
    def build_restraint_file(self, replica):
        """Builds restraint file for replica, based on template file
        """

        template = self.work_dir_local + "/" + self.input_folder + "/" + self.us_template
        try:
            r_file = open(template, "r")
            tbuffer = r_file.read()
            r_file.close()
        except IOError:
            self.logger.info("Warning: unable to access file: {0}".format(self.us_template) )

        i = replica.id

        try:
            w_file = open(replica.new_restraints, "w")
            tbuffer = tbuffer.replace("@val1@", str(replica.rstr_val_1))
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            self.logger.info("Warning: unable to access file: {0}".format(replica.new_restraints) )


    #-----------------------------------------------------------------------------------------------
    #
    def build_input_file(self, replica):
        """Builds input file for replica, based on template input file ala10.mdin
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

        try:
            r_file = open( (os.path.join((self.work_dir_local + "/" + self.input_folder + "/"), self.amber_input)), "r")
        except IOError:
            self.logger.error("Warning: unable to access template file: {0}".format(self.amber_input) )

        tbuffer = r_file.read()
        r_file.close()
      
        tbuffer = tbuffer.replace("@nstlim@",str(self.cycle_steps))
        tbuffer = tbuffer.replace("@temp@",str(int(replica.new_temperature)))
        tbuffer = tbuffer.replace("@salt@",str(float(replica.new_salt_concentration)))
        tbuffer = tbuffer.replace("@disang@",replica.new_restraints)
        
        replica.cycle += 1

        try:
            w_file = open(new_input_file, "w")
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            self.logger.error("Warning: unable to access file: {0}".format(new_input_file) )
     
#-----------------------------------------------------------------------------------------------------------------------------------
    def prepare_replica_for_md(self, replica, sd_shared_list):
        """
        """

        # need to avoid this step!
        self.build_input_file(replica)
      
        crds = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_coordinates

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
            # files needed to be moved in replica dir
            in_list = []
            for i in range(3):
                in_list.append(sd_shared_list[i])

            rid = replica.id
            in_list.append(sd_shared_list[rid+7])

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
            cu.mpi = self.md_replica_mpi
            cu.arguments = ["-O", "-i ", input_file, 
                                  "-o ", output_file, 
                                  "-p ", self.amber_parameters, 
                                  "-c ", self.amber_coordinates, 
                                  "-r ", new_coor, 
                                  "-x ", new_traj, 
                                  "-inf ", new_info]

            cu.cores = self.md_replica_cores
            cu.input_staging = [str(input_file), str(crds)] + in_list
            cu.output_staging = st_out
        else:

            # files needed to be moved in replica dir
            in_list = []

            rid = replica.id
            in_list.append(sd_shared_list[0])

            rstr_id = self.get_rstr_id(replica.new_restraints)
            in_list.append(sd_shared_list[rstr_id+7])

            #old_coor = replicas[r].first_path + "/" + self.amber_coordinates
            replica_path = "/replica_%d_%d/" % (replica.id, 0)
            old_coor = "../staging_area/" + replica_path + self.amber_coordinates
            cu = radical.pilot.ComputeUnitDescription()
            cu.executable = self.amber_path
            cu.pre_exec = self.pre_exec
            cu.mpi = self.md_replica_mpi
            cu.arguments = ["-O", "-i ", input_file, 
                                  "-o ", output_file, 
                                  "-p ", self.amber_parameters, 
                                  "-c ", old_coor, 
                                  "-r ", new_coor, 
                                  "-x ", new_traj, 
                                  "-inf ", new_info]

            cu.cores = self.md_replica_cores
            cu.input_staging = [str(input_file)] + in_list
            cu.output_staging = st_out

        return cu

    #------------------------------------------------------------------------------------------------------------------
    #
    def prepare_lists(self, replicas):

        """
        all_salt = ""
        all_temp = ""
        all_rstr = ""
        for r in range(len(replicas)):
            if r == 0:
                all_salt = str(replicas[r].new_salt_concentration)
                all_temp = str(replicas[r].new_temperature)
                all_rstr = str(replicas[r].new_restraints)
            else:
                all_salt = all_salt + " " + str(replicas[r].new_salt_concentration)
                all_temp = all_temp + " " + str(replicas[r].new_temperature)
                all_rstr = all_rstr + " " + str(replicas[r].new_restraints)

        self.all_temp_list = all_temp.split(" ")
        self.all_salt_list = all_salt.split(" ")
        self.all_rstr_list = all_rstr.split(" ")
        """

        pass

    #-----------------------------------------------------------------------------------------------------------------
    #
    def prepare_replica_for_exchange(self, dimension, replicas, replica, sd_shared_list):
        """
        """
        # name of the file which contains swap matrix column data for each replica
        basename = self.inp_basename
        matrix_col = "matrix_column_%s_%s.dat" % (str(replica.id), str(replica.cycle-1))

        current_group = self.get_current_group(dimension, replicas, replica)

        cu = radical.pilot.ComputeUnitDescription()
        if dimension == 1:

            data = {
                "replica_id": str(replica.id),
                "replica_cycle" : str(replica.cycle-1),
                "base_name" : str(basename),
                "current_group" : current_group,
                "replicas" : str(len(replicas)),
                "amber_parameters": "../staging_area/"+str(self.amber_parameters)
            }

            dump_data = json.dumps(data)
            json_data = dump_data.replace("\\", "")

            cu.executable = "python"
            cu.input_staging  = sd_shared_list[3]
            cu.arguments = ["matrix_calculator_temp_ex.py", json_data]
            cu.cores = self.temp_ex_cores
            cu.mpi = self.temp_ex_mpi          
            cu.output_staging = matrix_col

        elif dimension == 2:
            # 
            current_group_tsu = {}
            for repl in replicas:
                if str(repl.id) in current_group:
                    current_group_tsu[str(repl.id)] = [str(repl.new_temperature), str(repl.new_salt_concentration), str(repl.new_restraints)]

            data = {
                "replica_id": str(replica.id),
                "replica_cycle" : str(replica.cycle-1),
                "replicas" : str(self.replicas),
                "base_name" : str(basename),
                "init_temp" : str(replica.new_temperature),
                "amber_path" : str(self.amber_path),
                "amber_input" : str(self.amber_input),
                "amber_parameters": "../staging_area/"+str(self.amber_parameters),    #temp fix
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
            in_list.append(sd_shared_list[2])
            in_list.append(sd_shared_list[5])
            in_list.append(sd_shared_list[6])

            # copying .RST files from staging area to replica folder
            rst_group = []
            for k in current_group_tsu.keys():
                rstr_id = self.get_rstr_id(current_group_tsu[k][2])
                rst_group.append(rstr_id)

            for i in range(7,self.replicas+7):
                if (i-7) in rst_group:
                    in_list.append(sd_shared_list[i])
      
            cu.input_staging = in_list

            if self.salt_ex_cores > self.replicas:
                cu.arguments = ['-ng', str(self.replicas), '-groupfile', 'groupfile']
                cu.cores = self.salt_ex_cores
            else:
                cu.arguments = ['-ng', str(self.salt_ex_cores), '-groupfile', 'groupfile']
                cu.cores = self.salt_ex_cores

            cu.mpi = self.salt_ex_mpi
            cu.output_staging = matrix_col 
        else:

            current_group_rst = {}
            for repl in replicas:
                if str(repl.id) in current_group:
                    current_group_rst[str(repl.id)] = str(repl.new_restraints)  

            in_list = []
            # copying calculator from staging area to cu folder
            in_list.append(sd_shared_list[4])
            rid = replica.id
            # copying .RST files from staging area to replica folder
            rst_group = []
            for k in current_group_rst.keys():
                rstr_id = self.get_rstr_id(current_group_rst[k])
                rst_group.append(rstr_id)
           
            for i in range(7,self.replicas+7):
                if (i-7) in rst_group:
                    in_list.append(sd_shared_list[i])

            # copy new coordinates from MD run to CU directory
            coor_directive = {'source': 'staging:///%s' % replica.new_coor,
                              'target': replica.new_coor,
                              'action': radical.pilot.COPY
            }

            input_file = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_input

            data = {
                "replica_id": str(rid),
                "replica_cycle" : str(replica.cycle-1),
                "replicas" : str(self.replicas),
                "base_name" : str(basename),
                "init_temp" : str(replica.new_temperature),
                "amber_input" : str(self.amber_input),
                "amber_parameters": str(self.amber_parameters),
                "current_group_rst" : current_group_rst
            }

            dump_data = json.dumps(data)
            json_data = dump_data.replace("\\", "")
            
            cu.pre_exec = self.pre_exec
            cu.executable = "python"
            cu.input_staging = [str(input_file)] + in_list + [coor_directive]
            cu.output_staging = matrix_col
            cu.arguments = ["matrix_calculator_us_ex.py", json_data]
            cu.cores = self.us_ex_cores   
            cu.mpi = self.us_ex_mpi    

        return cu

    #-----------------------------------------------------------------------------------------------------------------------------------
    #
    def exchange_params(self, dimension, replica_1, replica_2):
        
        if dimension == 1:
            self.logger.debug("[exchange_params] before: r1: {0} r2: {1}".format(replica_1.new_temperature, replica_2.new_temperature) )
            temp = replica_2.new_temperature
            replica_2.new_temperature = replica_1.new_temperature
            replica_1.new_temperature = temp
            self.logger.debug("[exchange_params] after: r1: {0} r2: {1}".format(replica_1.new_temperature, replica_2.new_temperature) )
        elif dimension == 2:
            self.logger.debug("[exchange_params] before: r1: {0:0.2f} r2: {1:0.2f}".format(replica_1.new_salt_concentration, replica_2.new_salt_concentration) )
            salt = replica_2.new_salt_concentration
            replica_2.new_salt_concentration = replica_1.new_salt_concentration
            replica_1.new_salt_concentration = salt
            self.logger.debug("[exchange_params] after: r1: {0:0.2f} r2: {1:0.2f}".format(replica_1.new_salt_concentration, replica_2.new_salt_concentration) )
        else:
            self.logger.debug("[exchange_params] before: r1: {0:0.2f} r2: {1:0.2f}".format(replica_1.new_restraints, replica_2.new_restraints) )
            rstr = replica_2.new_restraints
            replica_2.new_restraints = replica_1.new_restraints
            replica_1.new_restraints = rstr
            self.logger.debug("[exchange_params] after: r1: {0:0.2f} r2: {1:0.2f}".format(replica_1.new_restraints, replica_2.new_restraints) )

    #-----------------------------------------------------------------------------------------------------------------------------------
    #
    def do_exchange(self, dimension, replicas, swap_matrix):

        self.logger.debug("[do_exchange] current dim: {0} replicas in current group: ".format(dimension) )
        #for r_i in replicas:
        #    self.logger.debug("[do_exchange] replica id: {0} salt: {1:0.2f} temp: {2} ".format(r_i.id, r_i.new_salt_concentration, r_i.new_temperature) )
          
        exchanged = []
        for r_i in replicas:
            r_j = self.gibbs_exchange(r_i, replicas, swap_matrix)
            self.logger.debug("[do_exchange] after gibbs_exchange: r_i.id: {0} r_j.id: {1}".format(r_i.id, r_j.id) )
            if (r_j.id != r_i.id) and (r_j.id not in exchanged) and (r_i.id not in exchanged):
                exchanged.append(r_j.id)
                exchanged.append(r_i.id)
                self.logger.debug("[do_exchange] EXCHANGE BETWEEN REPLICAS WITH ID'S: {0} AND {1} ".format(r_i.id, r_j.id) )
                # swap parameters
                self.exchange_params(dimension, r_i, r_j)
                # record that swap was performed
                r_i.swap = 1
                r_j.swap = 1

                # update id matrix
                if dimension == 1:
                    self.logger.debug("EXCHANGE Dim 1")
                    self.d1_id_matrix[r_i.id][self.current_cycle] = r_j.id
                    self.d1_id_matrix[r_j.id][self.current_cycle] = r_i.id
                elif dimension == 2:
                    self.logger.debug("EXCHANGE Dim 2")
                    self.d2_id_matrix[r_i.id][self.current_cycle] = r_j.id
                    self.d2_id_matrix[r_j.id][self.current_cycle] = r_i.id
                else:
                    self.logger.debug("EXCHANGE Dim 3")
                    self.d3_id_matrix[r_i.id][self.current_cycle] = r_j.id
                    self.d3_id_matrix[r_j.id][self.current_cycle] = r_i.id

        for replica in replicas:
            if dimension == 1:
                # update temp_matrix
                self.temp_matrix[replica.id][self.current_cycle] = replica.new_temperature
            elif dimension == 2:
                # update salt_matrix
                self.salt_matrix[replica.id][self.current_cycle] = replica.new_salt_concentration
            else:
                # update us_matrix
                self.us_matrix[replica.id][self.current_cycle] = replica.rstr_val_1

    #-----------------------------------------------------------------------------------------------------------------------------------
    #
    def select_for_exchange(self, dimension, replicas, swap_matrix, cycle):

        # updating rstr_val's
        for r in replicas:
            current_rstr = r.new_restraints
            try:
                r_file = open(current_rstr, "r")
            except IOError:
                self.logger.info("Warning: unable to access template file: {0}".format(current_rstr) )

            tbuffer = r_file.read()
            r_file.close()

            tbuffer = tbuffer.split()

            for word in tbuffer:
                if word.startswith("r2="):
                    num_list = word.split('=')
                    r.rstr_val_1 = float(num_list[1])
                
        self.current_cycle = cycle

        d1_list = []
        d2_list = []
        d3_list = []

        for r1 in replicas:
            ###############################################
            # temperature exchange
            if dimension == 1:
                r_pair = [r1.new_salt_concentration, r1.rstr_val_1]
                if r_pair not in d1_list:
                    d1_list.append(r_pair)
                    current_group = []

                    for r2 in replicas:
                        if (r1.new_salt_concentration == r2.new_salt_concentration) and (r1.rstr_val_1 == r2.rstr_val_1):
                            current_group.append(r2)

                    #######################################
                    # perform exchange among group members
                    #######################################
                    self.do_exchange(dimension, current_group, swap_matrix)
            ###############################################
            # salt concentration exchange
            elif dimension == 2:
                r_pair = [r1.new_temperature, r1.rstr_val_1]
                if r_pair not in d2_list:
                    d2_list.append(r_pair)
                    current_group = []
                    
                    for r2 in replicas:
                        if (r1.new_temperature == r2.new_temperature) and (r1.rstr_val_1 == r2.rstr_val_1):
                            current_group.append(r2)
                    
                    #######################################
                    # perform exchange among group members
                    #######################################
                    self.do_exchange(dimension, current_group, swap_matrix)
            ###############################################
            # us exchange d1
            else:
                r_pair = [r1.new_temperature, r1.new_salt_concentration]
                if r_pair not in d3_list:
                    d3_list.append(r_pair)
                    current_group = []
                    
                    for r2 in replicas:
                        if (r1.new_temperature == r2.new_temperature) and (r1.new_salt_concentration == r2.new_salt_concentration):
                            current_group.append(r2)
                    
                    #######################################
                    # perform exchange among group members
                    #######################################
                    self.do_exchange(dimension, current_group, swap_matrix)

        self.logger.debug("[select_for_exchange] after Dim: {0} d1_id_matrix: {1:s}".format(dimension, self.d1_id_matrix) )
        self.logger.debug("[select_for_exchange] after Dim: {0} d2_id_matrix: {1:s}".format(dimension, self.d2_id_matrix) )
        self.logger.debug("[select_for_exchange] after Dim: {0} d3_id_matrix: {1:s}".format(dimension, self.d3_id_matrix) )

    #-----------------------------------------------------------------------------------------------------------------------------------
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

        # salt_matrix
        for r in replicas:
            row = []
            row.append(r.id)
            row.append(r.new_salt_concentration)
            for c in range(self.nr_cycles - 1):
                row.append( -1.0 )

            self.salt_matrix.append( row )

        self.salt_matrix = sorted(self.salt_matrix)
        self.logger.debug("[init_matrices] salt_matrix: {0:s}".format(self.salt_matrix) )

        # us_matrix
        for r in replicas:
            row = []
            row.append(r.id)
            row.append(r.rstr_val_1)
            for c in range(self.nr_cycles - 1):
                row.append( -1.0 )
            self.us_matrix.append( row )

        self.us_matrix = sorted(self.us_matrix)
        self.logger.debug("[init_matrices] us_d1_matrix: {0:s}".format(self.us_matrix) )


    #-------------------------------------------------------------------------
    #
    def get_current_group(self, dimension, replicas, replica):
        """
        """

        current_group = []

        for r1 in replicas:
            
            ###############################################
            # temperature exchange
            if dimension == 1:
                
                r1_pair = [r1.new_salt_concentration, r1.rstr_val_1]
                my_pair = [replica.new_salt_concentration, replica.rstr_val_1]
                  
                if r1_pair == my_pair:
                    current_group.append(str(r1.id))

            ###############################################
            # salt concentration exchange
            elif dimension == 2:

                r1_pair = [r1.new_temperature, r1.rstr_val_1]
                my_pair = [replica.new_temperature, replica.rstr_val_1]

                if r1_pair == my_pair:
                    current_group.append(str(r1.id))

            ###############################################
            # us exchange 
            elif dimension == 3:

                r1_pair = [r1.new_temperature, r1.new_salt_concentration]
                my_pair = [replica.new_temperature, replica.new_salt_concentration]

                if r1_pair == my_pair:
                    current_group.append(str(r1.id))

        return current_group

