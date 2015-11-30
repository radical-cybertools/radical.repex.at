"""
.. module:: radical.repex.namd_kernels.namd_kernel_scheme_2
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
from os import path
import radical.pilot
from kernels.kernels import KERNELS
#from namd_kernel_tex import *

import radical.utils.logger as rul
#import namd_kernels_tex.namd_matrix_calculator_scheme_2

import namd_kernels_tex.global_ex_calculator
import namd_kernels_tex.ind_ex_calculator
import namd_kernels_tex.global_ex_calculator_mpi
import namd_kernels_tex.input_file_builder
from replicas.replica import *

#-------------------------------------------------------------------------------

class KernelPatternStex(object):

    def __init__(self, inp_file, rconfig,  work_dir_local):
        
        self.name = 'namd-tremd'
        self.ex_name = 'temperature'
        self.logger  = rul.getLogger ('radical.repex', self.name)
        
        self.namd_structure   = inp_file['remd.input'].get('namd_structure')
        self.namd_coordinates = inp_file['remd.input'].get('namd_coordinates')
        self.namd_parameters   = inp_file['remd.input'].get('namd_parameters')
 
        self.resource          = rconfig['target'].get('resource')
        self.cores         = int(rconfig['target'].get('cores', '1'))
        self.replicas      = int(inp_file['remd.input'].get('number_of_replicas'))
        self.cycle_steps   = int(inp_file['remd.input'].get('steps_per_cycle'))
        self.nr_cycles     = int(inp_file['remd.input'].get('number_of_cycles','1'))
        self.replica_cores = int(inp_file['remd.input'].get('replica_cores', '1'))

        if inp_file['remd.input'].get('exchange_mpi') == "True":
            self.exchange_mpi = True
        else:
            self.exchange_mpi = False

        self.min_temp = float(inp_file['remd.input'].get('min_temperature'))
        self.max_temp = float(inp_file['remd.input'].get('max_temperature'))
        self.work_dir_local    = work_dir_local
        self.current_cycle     = -1
        self.input_folder      = inp_file['remd.input'].get('input_folder')

        self.pre_exec = KERNELS[self.resource]["kernels"]["namd"]["pre_execution"]
        self.inp_basename = inp_file['remd.input']['input_file_basename']

        self.namd_path = inp_file['remd.input'].get('namd_path')
        if self.namd_path == None:
            self.logger.info("Using default NAMD path for: {0}".format(rconfig['target'].get('resource')))
            self.namd_path = KERNELS[self.resource]["kernels"]["namd"].get("executable")
        if self.namd_path == None:
            self.logger.info("NAMD path can't be found!")
            sys.exit(1)
        
        self.all_temp_list = []

        self.shared_urls = []
        self.shared_files = []

    #---------------------------------------------------------------------------
    #
    def prepare_shared_data(self, replicas):
 
        structure_path = self.work_dir_local + "/" + self.input_folder + "/" + self.namd_structure
        coords_path = self.work_dir_local + "/" + self.input_folder + "/" + self.namd_coordinates
        params_path = self.work_dir_local + "/" + self.input_folder + "/" + self.namd_parameters

        input_template = self.inp_basename + ".namd"
        input_template_path = self.work_dir_local + "/" + self.input_folder + "/" + input_template

        build_inp = os.path.dirname(namd_kernels_tex.input_file_builder.__file__)
        build_inp_path = build_inp + "/input_file_builder.py"

        global_calc = os.path.dirname(namd_kernels_tex.global_ex_calculator_mpi.__file__)
        global_calc_path = global_calc + "/global_ex_calculator_mpi.py"

        global_calc_s = os.path.dirname(namd_kernels_tex.global_ex_calculator.__file__)
        global_calc_path_s = global_calc_s + "/global_ex_calculator.py"

        ind_calc = os.path.dirname(namd_kernels_tex.ind_ex_calculator.__file__)
        ind_calc_path = ind_calc + "/ind_ex_calculator.py"

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
        self.shared_urls.append(global_calc_url)

        ind_calc_url = 'file://%s' % (ind_calc_path)
        self.shared_urls.append(ind_calc_url)

    #---------------------------------------------------------------------------
    #
    def initialize_replicas(self):
        
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
    """
    def build_input_file(self, replica):

        #-----------------------------------------------------------------------
        # copy to prepare_for_md

        data = {
            "basename": str(self.inp_basename),
            "replica_id": str(replica.id),
            "replica_cycle": str(replica.cycle),
            "cycle_steps": str(self.cycle_steps),
            "namd_structure": str(self.namd_structure),
            "namd_coordinates": str(self.namd_coordinates),
            "namd_parameters": str(self.namd_parameters),
            "replica_first_path"; str(replica.first_path),
            "replica_old_path"; str(replica.old_path),
            }
        dump_inp_data = json.dumps(data)
        json_inp_data_bash = dump_pre_data.replace("\\", "")

        #-----------------------------------------------------------------------


        basename = self.inp_basename[:-5]
        template = self.inp_basename
            
        new_input_file = "%s_%d_%d.namd" % (basename, replica.id, replica.cycle)
        outputname = "%s_%d_%d" % (basename, replica.id, replica.cycle)
        old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1))
        replica.new_coor = outputname + ".coor"
        replica.new_vel = outputname + ".vel"
        replica.new_history = outputname + ".history"
        replica.new_ext_system = outputname + ".xsc" 
        historyname = replica.new_history

        if (replica.cycle == 0):
            first_step = 0
        elif (replica.cycle == 1):
            first_step = int(self.cycle_steps)
        else:
            first_step = (replica.cycle - 1) * int(self.cycle_steps)

        if (replica.cycle == 0):
            old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1)) 
            structure = self.namd_structure
            coordinates = self.namd_coordinates
            parameters = self.namd_parameters
        else:
            old_name = replica.old_path + "/%s_%d_%d" % (basename, replica.id, (replica.cycle-1))
            structure = replica.first_path + "/" + self.namd_structure
            coordinates = replica.first_path + "/" + self.namd_coordinates
            parameters = replica.first_path + "/" + self.namd_parameters

        # substituting tokens in main replica input file 
        try:
            r_file = open( (os.path.join((self.work_dir_local + "/namd_inp/"), template)), "r")
        except IOError:
            print 'Warning: unable to access template file %s' % template

        tbuffer = r_file.read()
        r_file.close()

        tbuffer = tbuffer.replace("@swap@",str(replica.swap))
        tbuffer = tbuffer.replace("@ot@",str(replica.old_temperature))
        tbuffer = tbuffer.replace("@nt@",str(replica.new_temperature))
        tbuffer = tbuffer.replace("@steps@",str(self.cycle_steps))
        tbuffer = tbuffer.replace("@rid@",str(replica.id))
        tbuffer = tbuffer.replace("@somename@",str(outputname))
        tbuffer = tbuffer.replace("@oldname@",str(old_name))
        tbuffer = tbuffer.replace("@cycle@",str(replica.cycle))
        tbuffer = tbuffer.replace("@firststep@",str(first_step))
        tbuffer = tbuffer.replace("@history@",str(historyname))
        tbuffer = tbuffer.replace("@structure@", str(structure))
        tbuffer = tbuffer.replace("@coordinates@", str(coordinates))
        tbuffer = tbuffer.replace("@parameters@", str(parameters))
        
        replica.cycle += 1
        # write out
        try:
            w_file = open( new_input_file, "w")
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            print 'Warning: unable to access file %s' % new_input_file
    """

    #---------------------------------------------------------------------------
    #
    def prepare_replica_for_md(self, replica, sd_shared_list):
        
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
            'action': radical.pilot.COPY
        }
        stage_out.append(history_out)
        
        coor_out = {
            'source': new_coor,
            'target': 'staging:///%s' % new_coor,
            'action': radical.pilot.COPY
        }                   
        stage_out.append(coor_out)        

        vel_out = {
            'source': new_vel,
            'target': 'staging:///%s' % new_vel,
            'action': radical.pilot.COPY
        }
        stage_out.append(vel_out)
        
        ext_out = {
            'source': new_ext_system,
            'target': 'staging:///%s' % new_ext_system,
            'action': radical.pilot.COPY
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
            "old_temperature": str(replica.old_temperature),
            "new_temperature": str(replica.new_temperature),
            }
        dump_pre_data = json.dumps(data)
        json_pre_data = dump_pre_data.replace("\\", "")

        pre_exec_str = "python input_file_builder.py " + "\'" + json_pre_data + "\'"

        print "replica.cycle: {0}".format(replica.cycle)
        # only for first cycle we transfer structure, coordinates and parameters files
        if replica.cycle == 0:
            for i in range(5):
                stage_in.append(sd_shared_list[i])

            cu = radical.pilot.ComputeUnitDescription()
            cu.pre_exec   = self.pre_exec + [pre_exec_str]
            cu.executable = self.namd_path
            cu.arguments  = [input_file]
            cu.cores      = replica.cores
            cu.mpi = False
            cu.input_staging = stage_in
            cu.output_staging = stage_out
            
        else:
            """
            print "old_coor: {0}".format( old_coor )
            coor_in = {
            'source': 'staging:///%s' % old_coor,
            'target': old_coor,
            'action': radical.pilot.COPY
            }
            stage_in.append(coor_in)

            print "old_vel: {0}".format( old_vel )
            vel_in = {
            'source': 'staging:///%s' % old_vel,
            'target': old_vel,
            'action': radical.pilot.COPY
            }
            stage_in.append(vel_in)

            print "old_ext_system: {0}".format( old_ext_system )
            ext_in = {
            'source': 'staging:///%s' % old_ext_system,
            'target': old_ext_system,
            'action': radical.pilot.COPY
            }
            stage_in.append(ext_in)
            """

            stage_in.append(sd_shared_list[0])
            stage_in.append(sd_shared_list[1])
            stage_in.append(sd_shared_list[2])
            stage_in.append(sd_shared_list[3])
            stage_in.append(sd_shared_list[4])

            cu = radical.pilot.ComputeUnitDescription()
            cu.pre_exec    = self.pre_exec + [pre_exec_str]
            cu.executable = self.namd_path
            cu.arguments = [input_file]
            cu.cores = replica.cores
            cu.mpi = False
            cu.input_staging = stage_in
            cu.output_staging = stage_out

        replica.cycle += 1
        return cu

    #---------------------------------------------------------------------------
    #
    def prepare_replica_for_exchange(self, replica, sd_shared_list):
        
        """   
        # name of the file which contains swap matrix column data for each replica
        matrix_col = "matrix_column_%s_%s.dat" % (replica.id, (replica.cycle-1))
        basename = self.inp_basename[:-5]
        cu = radical.pilot.ComputeUnitDescription()
        cu.executable = "python"
        # each scheme has it's own calculator!
        calculator_path = os.path.dirname(namd_kernels_tex.namd_matrix_calculator_scheme_2.__file__)
        calculator = calculator_path + "/namd_matrix_calculator_scheme_2.py"
        cu.input_staging = [calculator] + sd_shared_list
        cu.arguments = ["namd_matrix_calculator_scheme_2.py", replica.id, (replica.cycle-1), self.replicas, basename]
        cu.cores = 1            
            
        return cu
        """
        pass
           
    #---------------------------------------------------------------------------
    #
    def prepare_global_ex_calc(self, GL, current_cycle, replicas, sd_shared_list):

        stage_out = []
        stage_in = []
        cycle = replicas[0].cycle-1

        outfile = "pairs_for_exchange_{cycle}.dat".format(cycle=cycle)
        stage_out.append(outfile)

        if self.exchange_mpi == True:
            # global_ex_calculator_mpi.py file
            stage_in.append(sd_shared_list[5])

            cu = radical.pilot.ComputeUnitDescription()
            cu.pre_exec = self.pre_exec
            cu.executable = "python"
            cu.input_staging  = stage_in
            cu.arguments = ["global_ex_calculator_mpi.py", str(cycle), str(self.replicas), str(self.inp_basename)]

            # guard for supermic
            if self.replicas > 999:
                cu.cores = self.replicas / 2
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
