"""
.. module:: radical.repex.md_kernles.amber_kernels_3d.amber_kernel_3d_pattern_b
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
from md_kernels.md_kernel_3d import *
import amber_kernels_3d.amber_matrix_calculator_pattern_b_tex
import amber_kernels_3d.amber_matrix_calculator_pattern_b_us

#--------------------------------------------------------------------------------------------------------------------------

class AmberKernel3dPatternB(MdKernel3d):
    """This class is responsible for performing all operations related to Amber for RE scheme S2.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.
    """
    def __init__(self, inp_file,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        MdKernel3d.__init__(self, inp_file, work_dir_local)

        self.pre_exec = KERNELS[self.resource]["kernels"]["amber"]["pre_execution"]
        try:
            self.amber_path = inp_file['input.MD']['amber_path']
        except:
            print "Using default Amber path for %s" % inp_file['input.PILOT']['resource']
            try:
                self.amber_path = KERNELS[self.resource]["kernels"]["amber"]["executable"]
            except:
                print "Amber path for localhost is not defined..."

        self.name = 'ak-patternB-3d'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        self.shared_urls = []
        self.shared_files = []

        self.all_temp_list = []
        self.all_rstr_list = []

        self.d1_id_matrix = []
        self.d2_id_matrix = []
        self.d3_id_matrix = []        

        self.temp_matrix = []
        self.us_d1_matrix = []
        self.us_d3_matrix = []

    #---------------------------------------------------------------------------------------------------------------------
    #
    def prepare_shared_data(self):

        parm_path = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_parameters
        rstr_path = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_restraints
        coor_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_coordinates
        inp_path  = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_input

        calc_tex = os.path.dirname(amber_kernels_3d.amber_matrix_calculator_pattern_b_tex.__file__)
        calc_tex_path = calc_tex + "/amber_matrix_calculator_pattern_b_tex.py"

        calc_us = os.path.dirname(amber_kernels_3d.amber_matrix_calculator_pattern_b_us.__file__)
        calc_us_path = calc_us + "/amber_matrix_calculator_pattern_b_us.py"

        rstr_list = []
        for rstr in self.restraints_files:
            rstr_list.append(self.work_dir_local + "/" + rstr)

        #------------------------------------------------
        self.shared_files.append(self.amber_parameters)
        self.shared_files.append(self.amber_restraints)
        self.shared_files.append(self.amber_coordinates)
        self.shared_files.append(self.amber_input)
        self.shared_files.append("amber_matrix_calculator_pattern_b_tex.py")
        self.shared_files.append("amber_matrix_calculator_pattern_b_us.py")

        for rstr in self.restraints_files:
            self.shared_files.append(rstr)
        #------------------------------------------------

        parm_url = 'file://%s' % (parm_path)
        self.shared_urls.append(parm_url)

        rstr_url = 'file://%s' % (rstr_path)
        self.shared_urls.append(rstr_url)

        coor_url = 'file://%s' % (coor_path)
        self.shared_urls.append(coor_url)

        inp_url = 'file://%s' % (inp_path)
        self.shared_urls.append(inp_url)

        calc_tex_url = 'file://%s' % (calc_tex_path)
        self.shared_urls.append(calc_tex_url)

        calc_us_url = 'file://%s' % (calc_us_path)
        self.shared_urls.append(calc_us_url)

        for rstr_p in rstr_list:
            rstr_url = 'file://%s' % (rstr_p)
            self.shared_urls.append(rstr_url)
 
    #---------------------------------------------------------------------------------------------------------------------
    #  
    def build_restraint_file(self, replica):
        """Builds restraint file for replica, based on template file
        """

        template = self.work_dir_local + "/" + self.input_folder + "/" + self.us_template
        r_file = open(template, "r")
        tbuffer = r_file.read()
        r_file.close()

        # hardcoded for now but can be arguments as well
        i = replica.id
        spacing_d1 = (self.us_end_param_d1 - self.us_start_param_d1) / float(self.replicas_d1)
        starting_value_d1 = self.us_start_param_d1 + i*spacing_d1

        spacing_d3 = (self.us_end_param_d3 - self.us_start_param_d3) / float(self.replicas_d3)
        starting_value_d3 = self.us_start_param_d3 + i*spacing_d3

        w_file = open(self.us_template+"."+str(i), "w")
        tbuffer = tbuffer.replace("@val1@", str(starting_value_d1+spacing_d1))
        tbuffer = tbuffer.replace("@val2@", str(starting_value_d3+spacing_d3))
        w_file.write(tbuffer)
        w_file.close()


    #---------------------------------------------------------------------------------------------------------------------
    #  
    def rebuild_restraint_file(self, replica):
        """Builds restraint file for replica, based on template file
        """

        r_file = open(replica.new_restraints_1, "r")
        tbuffer = r_file.read()
        r_file.close()
        tbuffer = tbuffer.split()

        line = 2
        for i in range(len(tbuffer)):
            word = tbuffer[i]
            if word == '/':
                line = 3
            if word.startswith("r2=") and line == 2:
                tbuffer[i] = "r2=" + str(replica.rstr_val_d1)
            if word.startswith("r3=") and line == 2:
                tbuffer[i] = "r3=" + str(replica.rstr_val_d1)
                
            if word.startswith("r2=") and line == 3:
                tbuffer[i] = "r2=" + str(replica.rstr_val_d3)
            if word.startswith("r3=") and line == 3:
                tbuffer[i] = "r2=" + str(replica.rstr_val_d3)
   
        w_file.write(tbuffer)
        w_file.close()

    #---------------------------------------------------------------------------------------------------------------------
    #
    def build_input_file(self, replica):
        """Builds input file for replica, based on template input file ala10.mdin
        """
       
        self.rebuild_restraint_file(replica)

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
        tbuffer = tbuffer.replace("@disang@",replica.new_restraints_1)
        tbuffer = tbuffer.replace("@temp@",str(self.init_temperature))
        
        replica.cycle += 1

        try:
            w_file = open(new_input_file, "w")
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            print 'Warning: unable to access file %s' % new_input_file

     
    #---------------------------------------------------------------------------------------------------------------------
    #
    def prepare_replica_for_md(self, replica, sd_shared_list):
        """
        """

        self.build_input_file(replica)
      
        crds = self.work_dir_local + "/" + self.input_folder + "/" + self.amber_coordinates
        input_file = "%s_%d_%d.mdin" % (self.inp_basename, replica.id, (replica.cycle-1))
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
            for i in range(4):
                in_list.append(sd_shared_list[i])

            rid = replica.id
            in_list.append(sd_shared_list[rid+6])

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

            # restraint files are NOT! exchanged
            #r_name = replica.new_restraints_1
            #rst_id = ""
            #dot = False
            #for ch in r_name:
            #    if ch == '.':
            #        dot = True
            #    if ch.isdigit() and (dot == True):
            #        rst_id = rst_id + str(ch)
            
            in_list.append(sd_shared_list[0])
            in_list.append(sd_shared_list[1])
            in_list.append(sd_shared_list[rid+6])

            replica_path = "/replica_%d_%d/" % (replica.id, 0)
            old_coor = "../staging_area/" + replica_path + self.amber_coordinates

            cu = radical.pilot.ComputeUnitDescription()
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

    #---------------------------------------------------------------------------------------------------------------------
    #
    def prepare_lists(self, replicas):
        """
        """

        all_rstr = ""
        all_temp = ""
        for r in range(len(replicas)):
            if r == 0:
                all_rstr = str(replicas[r].new_restraints_1)
                all_temp   = str(replicas[r].new_temperature_1)
            else:
                all_rstr = all_rstr + " " + str(replicas[r].new_restraints_1)
                all_temp   = all_temp + " " + str(replicas[r].new_temperature_1)

        self.all_temp_list = all_temp.split(" ")
        self.all_rstr_list = all_rstr.split(" ")
     
    #---------------------------------------------------------------------------------------------------------------------
    #
    def prepare_replica_for_exchange(self, dimension, replicas, replica, sd_shared_list):
        """
        """
        # name of the file which contains swap matrix column data for each replica
        basename = self.inp_basename
        matrix_col = "matrix_column_%s_%s.dat" % (str(replica.cycle-1), str(replica.id))

        if dimension == 2:
            cu = radical.pilot.ComputeUnitDescription()
            cu.executable = "python"
            cu.input_staging  = sd_shared_list[4]
            cu.arguments = ["amber_matrix_calculator_pattern_b_tex.py", replica.id, (replica.cycle-1), self.replicas, basename]
            cu.cores = 1            
            cu.output_staging = matrix_col
        else:

            all_restraints = []
            for repl in replicas:
                all_restraints.append(str(repl.new_restraints_1))
        
            # name of the file which contains swap matrix column data for each replica
            basename = self.inp_basename
            matrix_col = "matrix_column_%s_%s.dat" % (str(replica.cycle-1), str(replica.id))

            cu = radical.pilot.ComputeUnitDescription()
            cu.pre_exec = self.pre_exec
            cu.executable = "python"
 
            in_list = []
            # copying calculator from staging area to cu folder
            in_list.append(sd_shared_list[5])
            rid = replica.id
            # copying .RST files from staging area to replica folder
            for i in range(6,self.replicas+6):
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
                "init_temp" : str(self.init_temperature),
                "amber_path" : str(self.amber_path),
                "amber_input" : str(self.amber_input),
                "amber_parameters": str(self.amber_parameters),
                "all_restraints" : all_restraints
            }

            dump_data = json.dumps(data)
            json_data = dump_data.replace("\\", "")
            
            cu.input_staging = [str(input_file)] + in_list + [coor_directive]
            cu.output_staging = matrix_col
            cu.arguments = ["amber_matrix_calculator_pattern_b_us.py", json_data]
            cu.cores = 1            

        return cu

    #---------------------------------------------------------------------------------------------------------------------
    #
    def exchange_params(self, dimension, replica_1, replica_2):
        """
        """
        
        if dimension == 2:
            self.logger.debug("[exchange_params] before: r1: {0} r2: {1}".format(replica_1.new_temperature_1, replica_2.new_temperature_1) )
            temp = replica_2.new_temperature_1
            replica_2.new_temperature_1 = replica_1.new_temperature_1
            replica_1.new_temperature_1 = temp
            self.logger.debug("[exchange_params] after: r1: {0} r2: {1}".format(replica_1.new_temperature_1, replica_2.new_temperature_1) )
        elif dimension == 1:
            self.logger.debug("[exchange_params] before: r1: {0:0.2f} r2: {1:0.2f}".format(replica_1.rstr_val_d1, replica_2.rstr_val_d1) )
            rstr = replica_2.rstr_val_d1
            replica_2.rstr_val_d1 = replica_1.rstr_val_d1
            replica_1.rstr_val_d1 = rstr
            self.logger.debug("[exchange_params] after: r1: {0:0.2f} r2: {1:0.2f}".format(replica_1.rstr_val_d1, replica_2.rstr_val_d1) )
        elif dimension == 3:
            self.logger.debug("[exchange_params] before: r1: {0:0.2f} r2: {1:0.2f}".format(replica_1.rstr_val_d3, replica_2.rstr_val_d3) )
            rstr = replica_2.rstr_val_d3
            replica_2.rstr_val_d3 = replica_1.rstr_val_d3
            replica_1.rstr_val_d3 = rstr
            self.logger.debug("[exchange_params] after: r1: {0:0.2f} r2: {1:0.2f}".format(replica_1.rstr_val_d3, replica_2.rstr_val_d3) )


    #---------------------------------------------------------------------------------------------------------------------
    #
    def do_exchange(self, dimension, replicas, swap_matrix):
        """
        """

        self.logger.debug("[do_exchange] current dim: {0} replicas in current group: ".format(dimension) )
        for r_i in replicas:
            self.logger.debug("[do_exchange] replica id: {0} restr: {1} temp: {2} ".format(r_i.id, r_i.new_restraints_1, r_i.new_temperature_1) )
          
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


    #---------------------------------------------------------------------------------------------------------------------
    #
    def select_for_exchange(self, dimension, replicas, swap_matrix, cycle):
        """
        """

        # updating rstr_val's
        for r in replicas:
            current_rstr = r.new_restraints_1
            try:
                r_file = open(current_rstr, "r")
            except IOError:
                print 'Warning: unable to access template file %s' % current_rstr

            tbuffer = r_file.read()
            r_file.close()

            tbuffer = tbuffer.split()

            line = 2
            for word in tbuffer:
                if word == '/':
                    line = 3
                if word.startswith("r2=") and line == 2:
                    num_list = word.split('=')
                    r.rstr_val_d1 = float(num_list[1])
                if word.startswith("r2=") and line == 3:
                    num_list = word.split('=')
                    r.rstr_val_d3 = float(num_list[1])

        self.current_cycle = cycle

        d1_list = []
        d2_list = []
        d3_list = []

        for r1 in replicas:
            current_temp = r1.new_temperature_1
            
            ###############################################
            # temperature exchange
            if dimension == 2:
                r_pair = [r1.rstr_val_d1, r1.rstr_val_d3]
                if r_pair not in d2_list:
                    d2_list.append(r_pair)
                    current_group = []

                    for r2 in replicas:
                        if (r1.rstr_val_d1 == r2.rstr_val_d1) and (r1.rstr_val_d3 == r2.rstr_val_d3):
                            current_group.append(r2)

                    #######################################
                    # perform exchange among group members
                    #######################################
                    self.do_exchange(dimension, current_group, swap_matrix)
            ###############################################
            # us exchange d1
            elif dimension == 1:
                r_pair = [r1.new_temperature_1, r1.rstr_val_d3]

                if r_pair not in d1_list:
                    d1_list.append(r_pair)
                    current_group = []
                    
                    for r2 in replicas:
                        if (r1.new_temperature_1 == r2.new_temperature_1) and (r1.rstr_val_d3 == r2.rstr_val_d3):
                            current_group.append(r2)
                    
                    #######################################
                    # perform exchange among group members
                    #######################################
                    self.do_exchange(dimension, current_group, swap_matrix)

            ###############################################
            # us exchange d3
            elif dimension == 3:
                r_pair = [r1.new_temperature_1, r1.rstr_val_d1]

                if r_pair not in d3_list:
                    d3_list.append(r_pair)
                    current_group = []
                    
                    for r2 in replicas:
                        if (r1.new_temperature_1 == r2.new_temperature_1) and (r1.rstr_val_d1 == r2.rstr_val_d1):
                            current_group.append(r2)
                    
                    #######################################
                    # perform exchange among group members
                    #######################################
                    self.do_exchange(dimension, current_group, swap_matrix)

       
    #---------------------------------------------------------------------------------------------------------------------
    #
    def init_matrices(self, replicas):

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
            row.append(r.new_temperature_1)
            for c in range(self.nr_cycles - 1):
                row.append( -1.0 )

            self.temp_matrix.append( row )

        self.temp_matrix = sorted(self.temp_matrix)
        self.logger.debug("[init_matrices] temp_matrix: {0:s}".format(self.temp_matrix) )

        # us_d1_matrix
        for r in replicas:
            row = []
            row.append(r.id)
            row.append(r.new_restraints_1)
            for c in range(self.nr_cycles - 1):
                row.append( -1.0 )
            self.us_d1_matrix.append( row )

        self.us_d1_matrix = sorted(self.us_d1_matrix)
        self.logger.debug("[init_matrices] us_d1_matrix: {0:s}".format(self.us_d1_matrix) )

       