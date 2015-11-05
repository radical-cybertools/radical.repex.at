"""
.. module:: radical.repex.amber_kernels.amber_kernel
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import time
import math
import json
from os import path
import radical.pilot
from replicas.replica import Replica
from radical.ensemblemd import Kernel
import remote_modules.input_file_builder
import remote_modules.global_ex_calculator
import remote_modules.matrix_calculator_temp_ex
from radical.ensemblemd.patterns.replica_exchange import ReplicaExchange

#-------------------------------------------------------------------------------

class AmberTex(ReplicaExchange):
    """
    TODO
    """
    def __init__(self, inp_file,  workdir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as 
        specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        self.replica_objects = None

        self.inp_basename = inp_file['input.MD']['input_file_basename']
        self.inp_folder = inp_file['input.MD']['input_folder']
        self.replicas = int(inp_file['input.MD']['number_of_replicas'])
        self.cores = int(inp_file['input.PILOT']['cores'])
        self.cycle_steps = int(inp_file['input.MD']['steps_per_cycle'])
        self.workdir_local = workdir_local
        self.nr_cycles = int(inp_file['input.MD']['number_of_cycles'])
       
        try:
            self.replica_mpi = inp_file['input.MD']['replica_mpi']
        except:
            self.replica_mpi = False
        try:
            self.replica_cores = inp_file['input.MD']['replica_cores']
        except:
            self.replica_cores = 1

        try:
            self.amber_path = inp_file['input.MD']['amber_path']
        except:
            print "Using default Amber path for %s" % inp_file['input.PILOT']['resource']
            self.amber_path = None
           
        self.min_temp = float(inp_file['input.MD']['min_temperature'])
        self.max_temp = float(inp_file['input.MD']['max_temperature'])
        self.amber_restraints = str(inp_file['input.MD']['amber_restraints'])
        self.amber_coordinates = inp_file['input.MD']['amber_coordinates']
        self.amber_parameters = inp_file['input.MD']['amber_parameters']

        self.shared_urls = []
        self.shared_files = []
        
    #---------------------------------------------------------------------------
    #
    def prepare_shared_data(self):
 
        parm_path = self.workdir_local + "/" + self.inp_folder + "/" + \
                    self.amber_parameters
        coor_path = self.workdir_local + "/" + self.inp_folder + "/" + \
                    self.amber_coordinates
        rstr_path = self.workdir_local + "/" + self.inp_folder + "/" + \
                    self.amber_restraints

        input_template = self.inp_basename[:-5] + ".mdin"
        input_template_path = self.workdir_local + "/" + self.inp_folder + "/" + input_template

        calc_temp_ex = os.path.dirname(remote_modules.matrix_calculator_temp_ex.__file__)
        calc_temp_ex_path = calc_temp_ex + "/matrix_calculator_temp_ex.py"

        build_inp = os.path.dirname(remote_modules.input_file_builder.__file__)
        build_inp_path = build_inp + "/input_file_builder.py"

        global_calc = os.path.dirname(remote_modules.global_ex_calculator.__file__)
        global_calc_path = global_calc + "/global_ex_calculator.py"

        #-----------------------------------------------------------------------
        self.shared_files.append(self.amber_parameters)
        self.shared_files.append(self.amber_coordinates)
        self.shared_files.append(self.amber_restraints)
        self.shared_files.append(input_template)
        self.shared_files.append("matrix_calculator_temp_ex.py")
        self.shared_files.append("input_file_builder.py")
        self.shared_files.append("global_ex_calculator.py")

        parm_url = 'file://%s' % (parm_path)
        self.shared_urls.append(parm_url)  

        coor_url = 'file://%s' % (coor_path)
        self.shared_urls.append(coor_url)   

        rstr_url = 'file://%s' % (rstr_path)
        self.shared_urls.append(rstr_url)

        inp_url = 'file://%s' % (input_template_path)
        self.shared_urls.append(inp_url)

        calc_temp_ex_url = 'file://%s' % (calc_temp_ex_path)
        self.shared_urls.append(calc_temp_ex_url)

        build_inp_url = 'file://%s' % (build_inp_path)
        self.shared_urls.append(build_inp_url)

        global_calc_url = 'file://%s' % (global_calc_path)
        self.shared_urls.append(global_calc_url)

    #---------------------------------------------------------------------------
    #
    def initialize_replicas(self):
        replicas = []
        N = self.replicas
        factor = (self.max_temp/self.min_temp)**(1./(N-1))
        for k in range(N):
            new_temp = self.min_temp * (factor**k)
            r = Replica(k, new_temp)
            replicas.append(r)
            
        return replicas

    #---------------------------------------------------------------------------
    #
    def add_replicas(self, replicas):
        """Adds initialised replicas to this pattern.

        Arguments:
        replicas - list of replica objects
        """
        self.replica_objects = replicas

    #---------------------------------------------------------------------------
    #
    def get_replicas(self):
        """Returns a list of replica objects associated with this pattern.
        """
        return self.replica_objects

    #---------------------------------------------------------------------------
    # 
    def prepare_replica_for_md(self, replica):
        """Prepares all replicas for execution. In this function are created CU 
        descriptions for replicas, are specified input/output files to be 
        transferred to/from target system. Note: input files for first and 
        subsequent simulation cycles are different.

        Arguments:
        replicas - list of Replica objects

        Returns:
        compute_replicas - list of radical.pilot.ComputeUnitDescription objects
        """

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

        restraints = self.amber_restraints

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

        crds = self.workdir_local + "/" + \
               self.inp_folder + "/" + self.amber_coordinates
        parm = self.workdir_local + "/" + \
               self.inp_folder + "/" + self.amber_parameters
        rstr = self.workdir_local + "/" + \
               self.inp_folder + "/" + self.amber_restraints

        data = {
            "cycle_steps": str(self.cycle_steps),
            "new_restraints" : str(self.amber_restraints),
            "new_temperature" : str(replica.new_temperature),
            "amber_input" : str(template),
            "new_input_file" : str(new_input_file),
            "cycle" : str(replica.cycle)
                }
        dump_data = json.dumps(data)
        json_pre_data = dump_data.replace("\\", "")

        replica.cycle += 1

        data = {
            "replica_id": str(replica.id),
            "replica_cycle" : str(replica.cycle-1),
            "replicas" : str(self.replicas),
            "replica_basename" : str(basename),
            "new_temperature" : str(replica.new_temperature)
                }
        dump_data = json.dumps(data)
        json_post_data = dump_data.replace("\\", "")

        matrix_col = "matrix_column_{rid}_{cycle}.dat"\
                     .format(cycle=replica.cycle-1, rid=replica.id )

        if replica.cycle == 1:

            # sed magic
            #s1 = "sed -i \"s/{/'\{/\" run.sh;"
            #s2 = "sed -i \"s/@/'/\" run.sh;"
            #cu.executable = "chmod 755 run.sh;" + " " + s1 + " " + s2 + " ./run.sh"
            
            k = Kernel(name="md.amber")
            k.pre_exec  = ["python input_file_builder.py " + "\'" + \
                            json_pre_data + "\'"]
            k.uses_mpi = False
            k.arguments         = ["--mdinfile=" + input_file, 
                                   "--outfile="  + output_file, 
                                   "--params="   + self.amber_parameters, 
                                   "--coords="   + self.amber_coordinates, 
                                   "--nwcoords=" + new_coor, 
                                   "--nwtraj="   + new_traj, 
                                   "--nwinfo="   + new_info]

            k.copy_input_data = [ template,
                                 'input_file_builder.py',
                                 str(self.amber_parameters),
                                 str(self.amber_coordinates),
                                 str(restraints)]
            k.copy_output_data     = [str(new_info), 
                                      str(new_coor), 
                                      str(self.amber_coordinates)]
            k.cores                = int(self.replica_cores)
        else:
            #old_coor = replica.old_path + "/" + self.amber_coordinates
            old_coor = "../staging_area/" + self.amber_coordinates

            k = Kernel(name="md.amber")
            k.pre_exec  = ["python input_file_builder.py " + "\'" + \
                           json_pre_data + "\'"]
            k.uses_mpi = False

            k.arguments         = ["--mdinfile=" + input_file,
                                   "--outfile="  + output_file,
                                   "--params="   + self.amber_parameters,
                                   "--coords="   + old_coor,
                                   "--nwcoords=" + new_coor,
                                   "--nwtraj="   + new_traj,
                                   "--nwinfo="   + new_info]

            k.copy_input_data = [ template,
                                 'input_file_builder.py',
                                 str(self.amber_parameters),
                                 str(self.amber_coordinates),
                                 str(restraints)]
            k.copy_output_data     = [str(new_info), 
                                      str(new_coor), 
                                      str(self.amber_coordinates)]
            k.cores                = int(self.replica_cores)

        return k

    #---------------------------------------------------------------------------
    #
    def prepare_replica_for_exchange(self, replica):
        pass

    #---------------------------------------------------------------------------
    #
    def prepare_global_ex_calc(self, GL, current_cycle, replicas):
        """
        """

        basename = self.inp_basename

        cycle = replicas[0].cycle-1
        ex_pairs = "pairs_for_exchange_{cycle}.dat".format(cycle=cycle)

        k = Kernel(name="md.re_exchange")
        k.arguments = ["--calculator=global_ex_calculator.py",  
                       "--replica_cycle=" + str(cycle), 
                       "--replicas=" + str(self.replicas),
                       "--replica_basename=" + basename]
        k.subname = 'global_ex_calculator'
        k.pre_exec = ["module load python", "module load mpi4py"]
        k.copy_input_data  = ["global_ex_calculator.py"]
        k.download_output_data = [ex_pairs]
        if self.cores < self.replicas:
            k.cores = self.cores
        elif self.cores == self.replicas:
            k.cores = self.replicas
        k.mpi = True

        return k

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
