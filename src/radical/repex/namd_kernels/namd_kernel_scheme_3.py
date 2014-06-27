"""
.. module:: radical.repex.namd_kernels.namd_kernel_scheme_3
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
from kernels.kernels import KERNELS
from replicas.replica import Replica

#-----------------------------------------------------------------------------------------------------------------------------------

class NamdKernelScheme3(object):
    """This class is responsible for performing all operations related to NAMD for RE scheme 3.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.

    RE scheme 3:
    - Asynchronous RE scheme: MD run on target resource is overlapped with local exchange step. Thus both MD run
    and exchange step are asynchronous.  
    - Number of replicas is greater than number of allocated resources.
    - Replica simulation cycle is defined by the fixed number of simulation time-steps each replica has to perform.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed locally
    Overall algorithm is as follows:
        - First replicas in "waiting" state are submitted to pilot.
        - Then fixed time interval (cycle_time in input.json) must elapse before exchange step may take place.
        - After this fixed time interval elapsed, some replicas are still running on target resource.
        - In local exchange step are participating replicas which had finished MD run (state "finished") and
        replicas in "waiting" state.
        - After local exchanges step is performed replicas which participated in exchange are submitted to pilot
        to perform next simulation cycle
    """
    def __init__(self, inp_file,  work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        try:
            self.namd_path = inp_file['input.NAMD']['namd_path']
        except:
            print "Using default NAMD path for %s" % inp_file['input.PILOT']['resource']
            resource = inp_file['input.PILOT']['resource']
            self.namd_path = KERNELS[resource]["kernels"]["namd"]["executable"]
        self.inp_basename = inp_file['input.NAMD']['input_file_basename']
        self.inp_folder = inp_file['input.NAMD']['input_folder']
        self.namd_structure = inp_file['input.NAMD']['namd_structure']
        self.namd_coordinates = inp_file['input.NAMD']['namd_coordinates']
        self.namd_parameters = inp_file['input.NAMD']['namd_parameters']
        self.replicas = int(inp_file['input.NAMD']['number_of_replicas'])
        self.replica_cores = int(inp_file['input.NAMD']['replica_cores'])
        self.min_temp = float(inp_file['input.NAMD']['min_temperature'])
        self.max_temp = float(inp_file['input.NAMD']['max_temperature'])
        self.cycle_steps = int(inp_file['input.NAMD']['steps_per_cycle'])
        self.work_dir_local = work_dir_local

#----------------------------------------------------------------------------------------------------------------------------------

    #compute matrix of dimension-less energies: each column is a replica 
    #and each row is a state
    #so U[i][j] is the energy of replica j in state i. 
    #
    #Note that the matrix is sized to include all of the replicas and states 
    #but the energies of replicas not 
    #in waiting state, or those of waiting replicas for states not belonging to 
    #waiting replicas list are undefined.
    # OK
    def compute_swap_matrix(self, replicas):
        """        
        """
        # init matrix
        swap_matrix = [[ 0. for j in range(len(replicas))] 
             for i in range(len(replicas))]
 
        # updating replica temperatures and energies after md run
        for r in replicas:
                # getting OLDTEMP and POTENTIAL from .history file of previous run
                old_temp, old_energy = self.get_historical_data(r,(r.cycle-1))

                # updating replica temperature
                r.new_temperature = old_temp   
                r.old_temperature = old_temp   
                r.potential = old_energy

        for i in range(len(replicas)):
            repl_i = replicas[i]
            for j in range(len(replicas)):
                # here each column (representing replica) of U has all swappable results
                repl_j = replicas[j]
                swap_matrix[repl_j.sid][repl_i.id] = self.reduced_energy(repl_j.old_temperature,repl_i.potential)
        return swap_matrix

#----------------------------------------------------------------------------------------------------------------------------------

    def reduced_energy(self, temperature, potential):
        kb = 0.0019872041
        beta = 1. / (kb*temperature)     
        return float(beta * potential)

#----------------------------------------------------------------------------------------------------------------------------------

    def gibbs_exchange(self, r_i, replicas, swap_matrix):
        """Produces a replica "j" to exchange with the given replica "i"
        based off independence sampling of the discrete distribution

        Arguments:
        r_i - given replica for which is found partner replica
        replicas - list of Replica objects
        swap_matrix - matrix of dimension-less energies, where each column is a replica 
        and each row is a state

        Returns:
        r_j - replica to exchnage parameters with
        """
        #evaluate all i-j swap probabilities
        ps = [0.0]*(len(replicas))
  
        for j in range(len(replicas)):
            r_j = replicas[j]
            ps[j] = -(swap_matrix[r_i.sid][r_j.id] + swap_matrix[r_j.sid][r_i.id] - 
                      swap_matrix[r_i.sid][r_i.id] - swap_matrix[r_j.sid][r_j.id]) 

        new_ps = []
        for item in ps:
            new_item = math.exp(item)
            new_ps.append(new_item)
        ps = new_ps
        # index of swap replica within replicas_waiting list
        j = self.weighted_choice_sub(ps)
        # actual replica
        r_j = replicas[j]
        return r_j

#----------------------------------------------------------------------------------------------------------------------------------

    def weighted_choice_sub(self, weights):
        """Copy from AsyncRE code
        """

        rnd = random.random() * sum(weights)
        for i, w in enumerate(weights):
            rnd -= w
            if rnd < 0:
                return i

#----------------------------------------------------------------------------------------------------------------------------------

    def get_historical_data(self, replica, cycle):
        """Retrieves temperature and potential energy from simulaion output file <file_name>.history
        """
        if not os.path.exists(replica.new_history):
            print "history file not found: "
            print replica.new_history
        else:
            f = open(replica.new_history)
            lines = f.readlines()
            f.close()
            data = lines[0].split()
         
        return float(data[0]), float(data[1])

#----------------------------------------------------------------------------------------------------------------------------------

    def build_input_file(self, replica):
        """Generates input file for individual replica, based on template input file. Tokens @xxx@ are
        substituted with corresponding parameters. 
        In this function replica.cycle is incremented by one

        old_output_root @oldname@ determines which .coor .vel and .xsc files are used for next cycle

        Arguments:
        replica - a single Replica object
        """

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

        replica.old_coor = old_name + ".coor"
        replica.old_vel = old_name + ".vel"
        replica.old_ext_system = old_name + ".xsc" 

        if (replica.cycle == 0):
            first_step = 0
        elif (replica.cycle == 1):
            first_step = int(self.cycle_steps)
        else:
            first_step = (replica.cycle - 1) * int(self.cycle_steps)


        old_name = "%s_%d_%d" % (basename, replica.id, (replica.cycle-1)) 
        structure = self.namd_structure
        coordinates = self.namd_coordinates
        parameters = self.namd_parameters


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

#-----------------------------------------------------------------------------------------------------------------------------------

    def prepare_replicas(self, replicas, resource):
        """Creates a list of ComputeUnitDescription objects for MD simulation step. Here are
        specified input/output files to be transferred to/from target resource. Note: input 
        files for first and subsequent simulaition cycles are different.  

        Arguments:
        replicas - list of Replica objects
        resource - target resource identifier

        Returns:
        compute_replicas - list of radical.pilot.ComputeUnitDescription objects
        """
        compute_replicas = []
        for r in range(len(replicas)):
            self.build_input_file(replicas[r])
            input_file = "%s_%d_%d.namd" % (self.inp_basename[:-5], replicas[r].id, (replicas[r].cycle-1))

            new_coor = replicas[r].new_coor
            new_vel = replicas[r].new_vel
            new_history = replicas[r].new_history
            new_ext_system = replicas[r].new_ext_system

            old_coor = replicas[r].old_coor
            old_vel = replicas[r].old_vel
            old_ext_system = replicas[r].old_ext_system 

            # only for first cycle we transfer structure, coordinates and parameters files
            if replicas[r].cycle == 1:
                cu = radical.pilot.ComputeUnitDescription()
                cu.pre_exec    = KERNELS[resource]["kernels"]["namd"]["pre_execution"]
                cu.executable = self.namd_path
                cu.arguments = [input_file]
                cu.cores = replicas[r].cores
                structure = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_structure
                coords = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_coordinates
                params = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_parameters

                cu.input_data = [input_file, structure, coords, params]
                cu.output_data = [new_coor, new_vel, new_history, new_ext_system ]

                compute_replicas.append(cu)
            else:
                cu = radical.pilot.ComputeUnitDescription()
                cu.pre_exec    = KERNELS[resource]["kernels"]["namd"]["pre_execution"]
                cu.executable = self.namd_path
                cu.arguments = [input_file]
                cu.cores = 1
                structure = self.inp_folder + "/" + self.namd_structure
                coords = self.inp_folder + "/" + self.namd_coordinates
                params = self.inp_folder + "/" + self.namd_parameters
                cu.input_data = [input_file]

                cu.input_data = [input_file, structure, coords, params, old_coor, old_vel, old_ext_system]
                cu.output_data = [new_coor, new_vel, new_history, new_ext_system ]
                compute_replicas.append(cu)

        return compute_replicas
            
#-----------------------------------------------------------------------------------------------------------------------------------

    def initialize_replicas(self):
        """Initializes replicas and their attributes to default values.

        Returns:
        replicas - list of Replica objects
        """
        replicas = []
        for k in range(self.replicas):
            # may consider to change this    
            new_temp = random.uniform(self.max_temp , self.min_temp) * 0.8
            r = Replica(k, new_temp, self.replica_cores)
            replicas.append(r)
            
        return replicas

#-----------------------------------------------------------------------------------------------------------------------------------

    def check_replicas(self, replicas):
        """
        """
        finished_replicas = []
        files = os.listdir( self.work_dir_local )

        for r in replicas:
            history_name =  self.inp_basename[:-5] + "_%s_%s.history" % ( r.id, (r.cycle-1) )
            for item in files:
                if (item.startswith(history_name)):
                    if r not in finished_replicas:
                        finished_replicas.append( r )

        return finished_replicas

