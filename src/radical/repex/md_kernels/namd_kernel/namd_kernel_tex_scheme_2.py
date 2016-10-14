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
from namd_kernel_tex import *
import namd_kernels_tex.namd_matrix_calculator_scheme_2
import radical.utils.logger as rul

#-----------------------------------------------------------------------------------------------------------------------------------

class NamdKernelTexScheme2(NamdKernelTex):
    """This class is responsible for performing all operations related to NAMD for RE scheme 2.
    In this class is determined how replica input files are composed, how exchanges are performed, etc.

    RE scheme 2:
    - Synchronous RE scheme: none of the replicas can start exchange before all replicas has finished MD run.
    Conversely, none of the replicas can start MD run before all replicas has finished exchange step. 
    In other words global barrier is present.   
    - Number of replicas is greater than number of allocated resources for both MD and exchange step.
    - Simulation cycle is defined by the fixed number of simulation time-steps for each replica.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed in decentralized fashion on target resource.

    """
    def __init__(self, inp_file, work_dir_local):
        """Constructor.

        Arguments:
        inp_file - package input file with Pilot and NAMD related parameters as specified by user 
        work_dir_local - directory from which main simulation script was invoked
        """

        self.shared_urls = []
        self.shared_files = []

        self.name = 'nk-patternB-tex'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        NamdKernelTex.__init__(self, inp_file, work_dir_local)


#----------------------------------------------------------------------------------------------------------------------------------

    # ------------------------------------------------------------------------------
    #
    def prepare_shared_data(self):
 
        structure_path = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_structure
        coords_path = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_coordinates
        params_path = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_parameters

        self.shared_files.append(self.namd_structure)
        self.shared_files.append(self.namd_coordinates)
        self.shared_files.append(self.namd_parameters)

        struct_url = 'file://%s' % (structure_path)
        self.shared_urls.append(struct_url)
 
        coords_url = 'file://%s' % (coords_path)
        self.shared_urls.append(coords_url)     

        params_url = 'file://%s' % (params_path)
        self.shared_urls.append(params_url)
    
    # ------------------------------------------------------------------------------
    #
    def build_input_file(self, replica):
        """Generates input file for individual replica, based on template input file. Tokens @xxx@ are
        substituted with corresponding parameters. 

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

#-----------------------------------------------------------------------------------------------------------------------------------

    def prepare_replica_for_md(self, replica, sd_shared_list):
        """Creates a list of ComputeUnitDescription objects for MD simulation step. Here are
        specified input/output files to be transferred to/from target resource. Note: input 
        files for first and subsequent simulaition cycles are different.  

        Arguments:
        replicas - list of Replica objects

        Returns:
        compute_replicas - list of radical.pilot.ComputeUnitDescription objects
        """
        
        self.build_input_file(replica)
        input_file = "%s_%d_%d.namd" % (self.inp_basename[:-5], replica.id, (replica.cycle-1))

        new_coor = replica.new_coor
        new_vel = replica.new_vel
        new_history = replica.new_history
        new_ext_system = replica.new_ext_system

        old_coor = replica.old_coor
        old_vel = replica.old_vel
        old_ext_system = replica.old_ext_system 

        st_out = []
 
        history_out = {
            'source': new_history,
            'target': 'staging:///%s' % new_history,
            'action': radical.pilot.COPY
        }
        st_out.append(history_out)
        
        coor_out = {
            'source': new_coor,
            'target': 'staging:///%s' % new_coor,
            'action': radical.pilot.COPY
        }                   
        st_out.append(coor_out)        

        vel_out = {
            'source': new_vel,
            'target': 'staging:///%s' % new_vel,
            'action': radical.pilot.COPY
        }
        st_out.append(vel_out)
        
        ext_out = {
            'source': new_ext_system,
            'target': 'staging:///%s' % new_ext_system,
            'action': radical.pilot.COPY
        }
        st_out.append(ext_out)

        # only for first cycle we transfer structure, coordinates and parameters files
        if replica.cycle == 1:
            cu = radical.pilot.ComputeUnitDescription()
            cu.pre_exec    = KERNELS[self.resource]["kernels"]["namd"]["pre_execution"]
            cu.executable = self.namd_path
            cu.arguments = [input_file]
            cu.cores = replica.cores
            cu.mpi = False
            cu.input_staging = [str(input_file)] + sd_shared_list
            cu.output_staging = st_out
            
        else:
            cu = radical.pilot.ComputeUnitDescription()
            cu.pre_exec    = KERNELS[self.resource]["kernels"]["namd"]["pre_execution"]
            cu.executable = self.namd_path
            cu.arguments = [input_file]
            cu.cores = replica.cores
            cu.mpi = False
            cu.input_staging = [str(input_file)] + sd_shared_list
            cu.output_staging = st_out

        return cu

#-----------------------------------------------------------------------------------------------------------------------------------

    def prepare_replica_for_exchange(self, replica, sd_shared_list):
        """Creates a list of ComputeUnitDescription objects for exchange step on resource.
        Number of matrix_calculator_scheme_2.py instances invoked on resource is equal to the number 
        of replicas. 

        Arguments:
        replicas - list of Replica objects

        Returns:
        exchange_replicas - list of radical.pilot.ComputeUnitDescription objects
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
            
