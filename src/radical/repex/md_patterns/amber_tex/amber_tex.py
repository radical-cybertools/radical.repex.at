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
from md_patterns.md_pattern import *
from radical.ensemblemd import Kernel
import remote_modules.input_file_builder
import remote_modules.global_ex_calculator
import remote_modules.matrix_calculator_temp_ex
from radical.ensemblemd.patterns.replica_exchange import ReplicaExchange

#-------------------------------------------------------------------------------

class AmberTex(MdPattern, ReplicaExchange):
    """
    TODO
    """
    def __init__(self, inp_file,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as 
        specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        MdPattern.__init__(self, inp_file, work_dir_local)

        try:
            self.amber_path = inp_file['input.MD']['amber_path']
        except:
            print "Using default Amber path for %s" % inp_file['input.PILOT']['resource']
            self.amber_path = None
           
        self.min_temp = float(inp_file['input.MD']['min_temperature'])
        self.max_temp = float(inp_file['input.MD']['max_temperature'])
        self.amber_restraints = inp_file['input.MD']['amber_restraints']
        self.amber_coordinates = inp_file['input.MD']['amber_coordinates']
        self.amber_parameters = inp_file['input.MD']['amber_parameters']

        self.shared_urls = []
        self.shared_files = []

        super(AmberTex, self).__init__(inp_file,  work_dir_local)
        
    #---------------------------------------------------------------------------
    #
    def prepare_shared_data(self):
 
        parm_path = self.work_dir_local + "/" + self.inp_folder + "/" + \
                    self.amber_parameters
        coor_path = self.work_dir_local + "/" + self.inp_folder + "/" + \
                    self.amber_coordinates
        rstr_path = self.work_dir_local + "/" + self.inp_folder + "/" + \
                    self.amber_restraints

        input_template = self.inp_basename[:-5] + ".mdin"
        input_template_path = self.work_dir_local + "/" + self.inp_folder + "/" + input_template

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
    # note this is for a single replica
    # OK
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

        # from build_input_file()
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

        replica.cycle += 1

        #####################################

        input_file = "%s_%d_%d.mdin" % (self.inp_basename, replica.id, (replica.cycle-1))

        # this is not transferred back
        output_file = "%s_%d_%d.mdout" % (self.inp_basename, replica.id, (replica.cycle-1))

        new_coor = replica.new_coor
        new_traj = replica.new_traj
        new_info = replica.new_info

        old_coor = replica.old_coor
        old_traj = replica.old_traj

        crds = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_coordinates
        parm = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_parameters
        rstr = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_restraints

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


        if replica.cycle == 1:

            k = Kernel(name="md.amber")
            inpo = "python input_file_builder.py " + "\'" + json_pre_data + "\'"
            #k._cu_def_pre_exec  = [inpo]
            k._cu_def_pre_exec  = ["bin/date"]
            k.arguments         = ["--mdinfile="      + input_file, 
                                   "--outfile="     + output_file, 
                                   "--params="     + self.amber_parameters, 
                                   "--coords="     + self.amber_coordinates, 
                                   "--nwcoords=" + new_coor, 
                                   "--nwtraj="   + new_traj, 
                                   "--nwinfo="   + new_info]

            k.upload_input_data    = [str(input_file), str(crds)]
            k.copy_output_data     = [str(new_info), 
                                      str(new_coor), 
                                      str(self.amber_coordinates)]
            k.cores                = int(self.replica_cores)
        else:
            #old_coor = replica.old_path + "/" + self.amber_coordinates
            old_coor = "../staging_area/" + self.amber_coordinates

            k = Kernel(name="md.amber")
            k.arguments         = ["--mdinfile="      + input_file,
                                   "--outfile="     + output_file,
                                   "--params="     + self.amber_parameters,
                                   "--coords="     + old_coor,
                                   "--nwcoords=" + new_coor,
                                   "--nwtraj="   + new_traj,
                                   "--nwinfo="   + new_info]
            #k.copy_input_data     = [str(old_coor)]
            k.copy_output_data    = [str(new_info), str(new_coor)]
            k.upload_input_data   = [str(input_file)]
            k.cores               = int(self.replica_cores)

        return k

    #---------------------------------------------------------------------------
    #
    def prepare_replica_for_exchange(self, replica):
        """Creates a list of ComputeUnitDescription objects for exchange step on resource.
        Number of matrix_calculator_s2.py instances invoked on resource is equal to the number 
        of replicas. 

        Arguments:
        replicas - list of Replica objects

        Returns:
        exchange_replicas - list of radical.pilot.ComputeUnitDescription objects
        """

        basename = self.inp_basename
        
        # path!
        calculator_path = os.path.dirname(remote_modules.amber_matrix_calculator_pattern_b.__file__)
        calculator = calculator_path + "/amber_matrix_calculator_pattern_b.py"

        matrix_col = "matrix_column_{cycle}_{replica}.dat"\
                     .format(cycle=replica.cycle-1, replica=replica.id )

        k = Kernel(name="md.re_exchange")
        k.arguments = ["--calculator=amber_matrix_calculator_pattern_b.py", 
                       "--replica_id=" + str(replica.id), 
                       "--replica_cycle=" + str(replica.cycle-1), 
                       "--replicas=" + str(self.replicas), 
                       "--replica_basename=" + str(basename)]
        k.upload_input_data = calculator
        k.download_output_data = matrix_col

        return k

    #---------------------------------------------------------------------------
    #
    def get_historical_data(self, replica, cycle):
        """Retrieves temperature and potential energy from simulaion output
        file <file_name>.history
        """

        temp = 0.0    #temperature
        eptot = 0.0   #potential
        if not os.path.exists(replica.new_history):
            print "history file %s not found" % replica.new_history
        else:
            f = open(replica.new_history)
            lines = f.readlines()
            f.close()

            for i in range(len(lines)):
                if "TEMP(K)" in lines[i]:
                    temp = float(lines[i].split()[8])
                elif "EPtot" in lines[i]:
                    eptot = float(lines[i].split()[8])

        return temp, eptot


    #---------------------------------------------------------------------------
    #
    # this is for pattern-c/scheme-3
    def check_replicas(self, replicas):

        finished_replicas = []
        files = os.listdir( self.work_dir_local )

        for r in replicas:

            history_name =  r.new_history
            for item in files:
                if (item.startswith(history_name)):
                    if r not in finished_replicas:
                        finished_replicas.append( r )

        return finished_replicas



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
