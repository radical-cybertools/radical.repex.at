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
import exchange_calculators.amber_matrix_calculator_pattern_b
from radical.ensemblemd.patterns.replica_exchange import ReplicaExchange

#-----------------------------------------------------------------------------------------------------------------------------------

class AmberTex(MdPattern, ReplicaExchange):
    """This class is responsible for performing all operations related to Amber for RE scheme S2.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.

    RE scheme S2:
    - Synchronous RE scheme: none of the replicas can start exchange before all replicas has finished MD run.
    Conversely, none of the replicas can start MD run before all replicas has finished exchange step. 
    In other words global barrier is present.   
    - Number of replicas is greater than number of allocated resources for both MD and exchange step.
    - Simulation cycle is defined by the fixed number of simulation time-steps for each replica.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed in decentralized fashion on target resource.

    """
    def __init__(self, inp_file,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
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
        
    # ------------------------------------------------------------------------------
    #
    def prepare_shared_data(self):
 
        parm_path = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_parameters
        rstr_path = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_restraints

        self.shared_files.append(self.amber_parameters)
        self.shared_files.append(self.amber_restraints)

        parm_url = 'file://%s' % (parm_path)
        self.shared_urls.append(parm_url)     

        rstr_url = 'file://%s' % (rstr_path)
        self.shared_urls.append(rstr_url)

    #-------------------------------------------------------------------------------
    #
    def get_shared_urls(self):
        return self.shared_urls

    #-------------------------------------------------------------------------------
    #
    def get_shared_files(self):
        return self.shared_files

    #-------------------------------------------------------------------------------
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
    
#-----------------------------------------------------------------------------------------------------------------------------------
    # needed only for Pattern-C
    def build_input_file_local(self, replica):
        """Builds input file for replica, based on template input file ala10.mdin
        """

        basename = self.inp_basename
        template = self.inp_basename[:-5] + ".mdin"
            
        new_input_file = "%s_%d_%d.mdin" % (basename, replica.id, replica.cycle)
        outputname = "%s_%d_%d.mdout" % (basename, replica.id, replica.cycle)
        old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1))

        # new files
        replica.new_coor = "%s_%d_%d.rst" % (basename, replica.id, replica.cycle)
        replica.new_traj = "%s_%d_%d.mdcrd" % (basename, replica.id, replica.cycle)
        replica.new_info = "%s_%d_%d.mdinfo" % (basename, replica.id, replica.cycle)

        # may be redundant
        replica.new_history = replica.new_info

        # old files
        replica.old_coor = old_name + ".rst"
        replica.old_traj = old_name + ".mdcrd"
        replica.old_info = old_name + ".mdinfo"

        try:
            r_file = open( (os.path.join((self.work_dir_local + "/amber_inp/"), template)), "r")
        except IOError:
            print 'Warning: unable to access template file %s' % template

        tbuffer = r_file.read()
        r_file.close()

        tbuffer = tbuffer.replace("@nstlim@",str(self.cycle_steps))
        tbuffer = tbuffer.replace("@temp@",str(int(replica.new_temperature)))
        tbuffer = tbuffer.replace("@rstr@", self.amber_restraints )
        
        replica.cycle += 1

        try:
            w_file = open(new_input_file, "w")
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            print 'Warning: unable to access file %s' % new_input_file

#-----------------------------------------------------------------------------------------------------------------------------------

    def build_input_file(self, replica):
        """Builds input file for replica, based on template input file ala10.mdin
        """

        basename = self.inp_basename
        template = self.inp_basename[:-5] + ".mdin"
            
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

        if (replica.cycle == 0):
            restraints = self.amber_restraints
        else:
            ##################################
            # changing first path from absolute 
            # to relative so that Amber can 
            # process it
            ##################################
            path_list = []
            for char in reversed(replica.first_path):
                if char == '/': break
                path_list.append( char )

            modified_first_path = ''
            for char in reversed( path_list ):
                modified_first_path += char

            modified_first_path = '../' + modified_first_path.rstrip()
            # restraints = modified_first_path + "/" + self.amber_restraints
            restraints = self.amber_restraints
            
        try:
            r_file = open( (os.path.join((self.work_dir_local + "/amber_inp/"), template)), "r")
        except IOError:
            print 'Warning: unable to access template file %s' % template

        tbuffer = r_file.read()
        r_file.close()

        tbuffer = tbuffer.replace("@nstlim@",str(self.cycle_steps))
        tbuffer = tbuffer.replace("@temp@",str(int(replica.new_temperature)))
        tbuffer = tbuffer.replace("@rstr@", restraints )
        
        replica.cycle += 1

        try:
            w_file = open(new_input_file, "w")
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            print 'Warning: unable to access file %s' % new_input_file

#-----------------------------------------------------------------------------------------------------------------------------------
    # needed only for Pattern-C
    def prepare_replicas_local(self, replicas):
        """Prepares all replicas for execution. In this function are created CU descriptions for replicas, are
        specified input/output files to be transferred to/from target system. Note: input files for first and 
        subsequent simulation cycles are different.
        """
        compute_replicas = []
        for r in range(len(replicas)):
            self.build_input_file_local(replicas[r])
            input_file = "%s_%d_%d.mdin" % (self.inp_basename, replicas[r].id, (replicas[r].cycle-1))

            # this is not transferred back
            output_file = "%s_%d_%d.mdout" % (self.inp_basename, replicas[r].id, (replicas[r].cycle-1))

            new_coor = replicas[r].new_coor
            new_traj = replicas[r].new_traj
            new_info = replicas[r].new_info

            old_coor = replicas[r].old_coor
            old_traj = replicas[r].old_traj
            old_info = replicas[r].old_info

            if replicas[r].cycle == 1:
                cu = radical.pilot.ComputeUnitDescription()
                crds = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_coordinates
                parm = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_parameters
                rstr = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_restraints

                cu.executable = self.amber_path
                cu.pre_exec = self.pre_exec
                cu.mpi = self.replica_mpi
                cu.arguments = ["-O", "-i ", input_file, "-o ", output_file, "-p ", self.amber_parameters, "-c ", self.amber_coordinates, "-r ", new_coor, "-x ", new_traj, "-inf ", new_info]
                cu.cores = self.replica_cores
                cu.input_staging = [str(input_file), str(crds), str(parm), str(rstr)]
                cu.output_staging = [str(new_coor), str(new_traj), str(new_info)]
                compute_replicas.append(cu)
            else:
                cu = radical.pilot.ComputeUnitDescription()
                
                crds = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_coordinates
                parm = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_parameters
                rstr = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_restraints
                cu.executable = self.amber_path
                cu.pre_exec = self.pre_exec
                cu.mpi = self.replica_mpi
                cu.arguments = ["-O", "-i ", input_file, "-o ", output_file, "-p ", self.amber_parameters, "-c ", old_coor, "-r ", new_coor, "-x ", new_traj, "-inf ", new_info]
                cu.cores = self.replica_cores

                cu.input_staging = [str(input_file), str(crds), str(parm), str(rstr), str(old_coor)]
                cu.output_staging = [str(new_coor), str(new_traj), str(new_info)]
                compute_replicas.append(cu)

        return compute_replicas

#-----------------------------------------------------------------------------------------------------------------------------------
    # note this is for a single replica
    # OK
    def prepare_replica_for_md(self, replica):
        """Prepares all replicas for execution. In this function are created CU descriptions for replicas, are
        specified input/output files to be transferred to/from target system. Note: input files for first and 
        subsequent simulation cycles are different.

        Arguments:
        replicas - list of Replica objects

        Returns:
        compute_replicas - list of radical.pilot.ComputeUnitDescription objects
        """
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

        if replica.cycle == 1:

            k = Kernel(name="md.amber")
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

#-----------------------------------------------------------------------------------------------------------------------------------

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
        calculator_path = os.path.dirname(exchange_calculators.amber_matrix_calculator_pattern_b.__file__)
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

#-----------------------------------------------------------------------------------------------------------------------------------

    # ok
    def get_historical_data(self, replica, cycle):
        """Retrieves temperature and potential energy from simulaion output file <file_name>.history
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


#-----------------------------------------------------------------------------------------------------------------------------------

    ########################################
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



#-------------------------------------------------------------------------------
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
