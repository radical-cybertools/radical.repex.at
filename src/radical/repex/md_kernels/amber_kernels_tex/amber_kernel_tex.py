"""
.. module:: radical.repex.amber_kernels.amber_kernel
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
from os import path
import radical.pilot
from kernels.kernels import KERNELS
from md_kernels.md_kernel_tex import *

#-----------------------------------------------------------------------------------------------------------------------------------

class AmberKernelTex(MdKernelTex):
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

        MdKernelTex.__init__(self, inp_file, work_dir_local)

        self.pre_exec = KERNELS[self.resource]["kernels"]["amber"]["pre_execution"]
        try:
            self.amber_path = inp_file['input.MD']['amber_path']
        except:
            print "Using default Amber path for %s" % inp_file['input.PILOT']['resource']
            try:
                self.amber_path = KERNELS[self.resource]["kernels"]["amber"]["executable"]
            except:
                print "Amber path for localhost is not defined..."

        self.amber_coordinates = inp_file['input.MD']['amber_coordinates']
        self.amber_parameters = inp_file['input.MD']['amber_parameters']
 
        self.input_folder = inp_file['input.MD']['input_folder']       

#-----------------------------------------------------------------------------------------------------------------------------------

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

        try:
            r_file = open( (os.path.join((self.work_dir_local + "/" + self.input_folder + "/"), template)), "r")
        except IOError:
            print 'Warning: unable to access template file %s' % template

        tbuffer = r_file.read()
        r_file.close()

        tbuffer = tbuffer.replace("@nstlim@",str(self.cycle_steps))
        tbuffer = tbuffer.replace("@temp@",str(int(replica.new_temperature)))
        
        replica.cycle += 1

        try:
            w_file = open(new_input_file, "w")
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            print 'Warning: unable to access file %s' % new_input_file


#-----------------------------------------------------------------------------------------------------------------------------------

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

                cu.executable = self.amber_path
                cu.pre_exec = self.pre_exec
                cu.mpi = self.replica_mpi
                cu.arguments = ["-O", "-i ", input_file, "-o ", output_file, "-p ", self.amber_parameters, "-c ", self.amber_coordinates, "-r ", new_coor, "-x ", new_traj, "-inf ", new_info]
                cu.cores = self.replica_cores
                cu.input_staging = [str(input_file), str(crds), str(parm)]
                cu.output_staging = [str(new_coor), str(new_traj), str(new_info)]
                compute_replicas.append(cu)
            else:
                cu = radical.pilot.ComputeUnitDescription()
                
                crds = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_coordinates
                parm = self.work_dir_local + "/" + self.inp_folder + "/" + self.amber_parameters
                cu.executable = self.amber_path
                cu.pre_exec = self.pre_exec
                cu.mpi = self.replica_mpi
                cu.arguments = ["-O", "-i ", input_file, "-o ", output_file, "-p ", self.amber_parameters, "-c ", old_coor, "-r ", new_coor, "-x ", new_traj, "-inf ", new_info]
                cu.cores = self.replica_cores

                cu.input_staging = [str(input_file), str(crds), str(parm), str(old_coor)]
                cu.output_staging = [str(new_coor), str(new_traj), str(new_info)]
                compute_replicas.append(cu)

        return compute_replicas

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
