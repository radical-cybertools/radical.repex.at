"""
.. module:: radical.repex.pilot_kernels.pilot_kernel_pattern_b
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import time
import math
import json
import datetime
from os import path
import radical.pilot
import radical.utils.logger as rul
from pilot_kernels.pilot_kernel import *

#-----------------------------------------------------------------------------------------------------------------------------------

class PilotKernelPatternB(PilotKernel):
    """This class is responsible for performing all Radical Pilot related operations for RE scheme 2.
    This includes pilot launching, running main loop of RE simulation and using RP API for data staging in and out. 

    RE pattern B:
    - Synchronous RE scheme: none of the replicas can start exchange before all replicas has finished MD run.
    Conversely, none of the replicas can start MD run before all replicas has finished exchange step. 
    In other words global barrier is present.   
    - Number of replicas is greater than number of allocated resources for both MD and exchange step.
    - Simulation cycle is defined by the fixed number of simulation time-steps for each replica.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed in decentralized fashion on target resource.
    """
    def __init__(self, inp_file):
        """Constructor.

        Arguments:
        inp_file - json input file with Pilot and NAMD related parameters as specified by user 
        """

        PilotKernel.__init__(self, inp_file)

        self.name = 'pk-patternB'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        self.sd_shared_list = []

    #---------------------------------------------------------
    #
    def build_swap_matrix(self, replicas):
        """Creates a swap matrix from matrix_column_x.dat files. 
        matrix_column_x.dat - is populated on targer resource and then transferred back. This
        file is created for each replica and has data for one column of swap matrix. In addition to that,
        this file holds path to pilot compute unit of the previous run, where reside NAMD output files for 
        a given replica. 

        Arguments:
        replicas - list of Replica objects

        Returns:
        swap_matrix - 2D list of lists of dimension-less energies, where each column is a replica 
        and each row is a state
        """

        base_name = "matrix_column"
        size = len(replicas)

        # init matrix
        swap_matrix = [[ 0. for j in range(size)]
             for i in range(size)]

        for r in replicas:
            column_file = base_name + "_" + str(r.cycle-1) + "_" + str(r.id) +  ".dat"       
            try:
                f = open(column_file)
                lines = f.readlines()
                f.close()
                data = lines[0].split()
                # populating one column at a time
                for i in range(size):
                    swap_matrix[i][r.id] = float(data[i])

                # setting old_path and first_path for each replica
                if ( r.cycle == 1 ):
                    r.first_path = str(data[size])
                    r.old_path = str(data[size])
                else:
                    r.old_path = str(data[size])
            except:
                raise

        return swap_matrix

    #-----------------------------------------------------------------------------------------------------
    #
    def compose_swap_matrix(self, replicas, matrix_columns):
        """Creates a swap matrix from matrix_column_x.dat files. 
        matrix_column_x.dat - is populated on target resource and then transferred back. This
        file is created for each replica and has data for one column of swap matrix. In addition to that,
        this file holds path to pilot compute unit of the previous run, where reside NAMD output files for 
        a given replica. 

        Arguments:
        replicas - list of Replica objects

        Returns:
        swap_matrix - 2D list of lists of dimension-less energies, where each column is a replica 
        and each row is a state
        """
 
        # init matrix
        swap_matrix = [[ 0. for j in range(len(replicas))] 
             for i in range(len(replicas))]

        matrix_columns = sorted(matrix_columns)

        for r in replicas:
            # populating one column at a time
            for i in range(len(replicas)):
                swap_matrix[i][r.id] = float(matrix_columns[r.id][i])

        return swap_matrix

#-----------------------------------------------------------------------------------------------------------------------------------

    def run_simulation(self, replicas, pilot_object, session,  md_kernel ):
        """This function runs the main loop of RE simulation for RE scheme 2a.

        Arguments:
        replicas - list of Replica objects
        pilot_object - radical.pilot.ComputePilot object
        session - radical.pilot.session object, the *root* object for all other RADICAL-Pilot objects 
        md_kernel - an instance of NamdKernelScheme2a class
        """
        # --------------------------------------------------------------------------
        #
        def unit_state_change_cb(unit, state):
            """This is a callback function. It gets called very time a ComputeUnit changes its state.
            """
            if unit:
                self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )

                if state == radical.pilot.states.FAILED:
                    self.logger.error("Log: {0:s}".format( unit.as_dict() ) )

        # --------------------------------------------------------------------------

        CYCLES = md_kernel.nr_cycles + 1
       
        unit_manager = radical.pilot.UnitManager(session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(pilot_object)

        # creating restraint files for US case 
        if md_kernel.name == 'ak-patternB-us':
            for r in replicas:
                md_kernel.build_restraint_file(r)

        # staging shared input data in
        md_kernel.prepare_shared_data()

        shared_input_file_urls = md_kernel.shared_urls
        shared_input_files = md_kernel.shared_files

        for i in range(len(shared_input_files)):

            sd_pilot = {'source': shared_input_file_urls[i],
                        'target': 'staging:///%s' % shared_input_files[i],
                        'action': radical.pilot.TRANSFER
            }

            pilot_object.stage_in(sd_pilot)

            sd_shared = {'source': 'staging:///%s' % shared_input_files[i],
                         'target': shared_input_files[i],
                         'action': radical.pilot.COPY
            }
            self.sd_shared_list.append(sd_shared)

        # make sure data is staged
        time.sleep(10)
        
        # absolute simulation start time
        start = datetime.datetime.utcnow()

        hl_performance_data = {}
        cu_performance_data = {}

        # bulk = 0: do sequential submission
        # bulk = 1: do bulk submission
        bulk = 0
        for current_cycle in range(1,CYCLES):

            hl_performance_data["cycle_{0}".format(current_cycle)] = {}
            cu_performance_data["cycle_{0}".format(current_cycle)] = {}

            self.logger.info("Performing cycle: {0}".format(current_cycle) )

            self.logger.info("Preparing {0} replicas for MD run; cycle {1}".format(md_kernel.replicas, current_cycle) )

            submitted_replicas = []
            ################################################################################
            # sequential submission
            outfile = "md_prep_submission_details_{0}.csv".format(session.uid)
            if bulk == 0:
                T1 = datetime.datetime.utcnow()
                for r in replicas:

                    with open(outfile, 'w+') as f:
                        t_1 = datetime.datetime.utcnow()
                        compute_replica = md_kernel.prepare_replica_for_md(r, self.sd_shared_list)
                        t_2 = datetime.datetime.utcnow()
                        value =  (t_2-t_1).total_seconds()
                        f.write("repex_md_prep_time {0}\n".format(value))

                        t_1 = datetime.datetime.utcnow()
                        sub_replica = unit_manager.submit_units(compute_replica)
                        t_2 = datetime.datetime.utcnow()
                        value = (t_2-t_1).total_seconds()
                        f.write("rp_submit_time {0}\n".format(value))

                        submitted_replicas.append(sub_replica)
                f.close()
                T2 = datetime.datetime.utcnow()
            ################################################################################
            # bulk submision
            else:
                c_replicas = []
                T1 = datetime.datetime.utcnow()

                t_1 = datetime.datetime.utcnow()
                for r in replicas:
                    compute_replica = md_kernel.prepare_replica_for_md(r, self.sd_shared_list)
                    c_replicas.append(compute_replica)
                t_2 = datetime.datetime.utcnow()

                with open(outfile, 'w+') as f:
                    value =  (t_2-t_1).total_seconds()
                    f.write("repex_md_prep_time {0}\n".format(value))

                    t_1 = datetime.datetime.utcnow()
                    submitted_replicas = unit_manager.submit_units(c_replicas)
                    t_2 = datetime.datetime.utcnow()
                    value = (t_2-t_1).total_seconds()
                    f.write("rp_submit_time {0}\n".format(value))
 
                T2 = datetime.datetime.utcnow()
            
            ################################################################################

            hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("MD_prep")] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("MD_prep")] = (T2-T1).total_seconds()

            self.logger.info("Submitting {0} replicas for MD run; cycle {1}".format(md_kernel.replicas, current_cycle) )
            T1 = datetime.datetime.utcnow()
            unit_manager.wait_units()
            T2 = datetime.datetime.utcnow()

            hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("MD")] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("MD")] = (T2-T1).total_seconds()

            cu_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("MD")] = {}
            for cu in submitted_replicas:
                cu_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("MD")]["cu.uid_{0}".format(cu.uid)] = cu
             
            # this is not done for the last cycle
            if (current_cycle < CYCLES):

                self.logger.info("Preparing {0} replicas for Exchange run; cycle {1}".format(md_kernel.replicas, current_cycle) )

                exchange_replicas = []

                ################################################################################
                # sequential submission
                outfile = "ex_prep_submission_details_{0}.csv".format(session.uid)
                if bulk == 0:
                    T1 = datetime.datetime.utcnow()
                    for r in replicas:
                        with open(outfile, 'w+') as f:
                            t_1 = datetime.datetime.utcnow()
                            exchange_replica = md_kernel.prepare_replica_for_exchange(replicas, r, self.sd_shared_list)
                            t_2 = datetime.datetime.utcnow()
                            value =  (t_2-t_1).total_seconds()
                            f.write("repex_ex_prep_time {0}\n".format(value))

                            t_1 = datetime.datetime.utcnow()
                            sub_replica = unit_manager.submit_units(exchange_replica)
                            t_2 = datetime.datetime.utcnow()
                            value =  (t_2-t_1).total_seconds()
                            f.write("rp_submit_time {0}\n".format(value))

                        exchange_replicas.append(sub_replica)
                    f.close()
                    T2 = datetime.datetime.utcnow()
                ################################################################################
                # bulk submision
                else:
                    e_replicas = []
                    T1 = datetime.datetime.utcnow()

                    t_1 = datetime.datetime.utcnow()
                    for r in replicas:
                        exchange_replica = md_kernel.prepare_replica_for_exchange(replicas, r, self.sd_shared_list)
                        e_replicas.append(exchange_replica)
                    t_2 = datetime.datetime.utcnow()
                    with open(outfile, 'w+') as f:
                        value =  (t_2-t_1).total_seconds()
                        f.write("repex_ex_prep_time {0}\n".format(value))
                   
                        t_1 = datetime.datetime.utcnow()
                        exchange_replicas = unit_manager.submit_units(e_replicas)
                        t_2 = datetime.datetime.utcnow()

                        value =  (t_2-t_1).total_seconds()
                        f.write("rp_submit_time {0}\n".format(value))

                    T2 = datetime.datetime.utcnow()

                ################################################################################

                hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("EX_prep")] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("EX_prep")] = (T2-T1).total_seconds()

                self.logger.info("Submitting {0} replicas for Exchange run; cycle {1}".format(md_kernel.replicas, current_cycle) )

                T1 = datetime.datetime.utcnow()
                unit_manager.wait_units()
                T2 = datetime.datetime.utcnow()

                hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("EX")] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("EX")] = (T2-T1).total_seconds()
 
                cu_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("EX")] = {}
                for cu in exchange_replicas:
                    cu_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("EX")]["cu.uid_{0}".format(cu.uid)] = cu

                # populating swap matrix                
                T1 = datetime.datetime.utcnow()
                matrix_columns = []
          
                for r in exchange_replicas:
                    if r.state != radical.pilot.DONE:
                        self.logger.error('Exchange step failed for unit:  %s' % r.uid)
                    #else:
                    #    d = str(r.stdout)
                    #    data = d.split()
                    #    data.append(r.uid)
                    #    matrix_columns.append(data)

                matrix_columns = self.build_swap_matrix(replicas)

                # writing swap matrix out
                sw_file = "swap_matrix_" + str(current_cycle)
                try:
                    w_file = open( sw_file, "w")
                    for i in matrix_columns:
                        for j in i:
                            w_file.write("%s " % j)
                        w_file.write("\n")
                    w_file.close()
                except IOError:
                    self.logger.info('Warning: unable to access file %s' % sw_file)

                self.logger.info("Composing swap matrix from individual files for all replicas")

                swap_matrix = self.compose_swap_matrix(replicas, matrix_columns)
            
                self.logger.info("Performing exchange")
                for r_i in replicas:
                    r_j = md_kernel.gibbs_exchange(r_i, replicas, swap_matrix)
                    if (r_j != r_i):
                        #
                        md_kernel.exchange_params(r_i, r_j)                    
                        #temperature = r_j.new_temperature
                        #r_j.new_temperature = r_i.new_temperature
                        #r_i.new_temperature = temperature
                        # record that swap was performed
                        r_i.swap = 1
                        r_j.swap = 1
                stop_time = datetime.datetime.utcnow()
                T2 = datetime.datetime.utcnow()

                hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("Post_processing")] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("Post_processing")] = (T2-T1).total_seconds()

        end = datetime.datetime.utcnow()
        RAW_SIMULATION_TIME = (end-start).total_seconds()

        outfile = "execution_profile_{mysession}.csv".format(mysession=session.uid)

        with open(outfile, 'w+') as f:
            f.write("Total simulaiton time: {row}\n".format(row=RAW_SIMULATION_TIME))

            #-----------------------------------------------
            head = "Cycle; Run; Duration"
            #print head
            f.write("{row}\n".format(row=head))

            for cycle in hl_performance_data:
                for run in hl_performance_data[cycle].keys():
                    duration = hl_performance_data[cycle][run]

                    row = "{Cycle}; {Run}; {Duration}".format(Duration=duration, Cycle=cycle, Run=run)

                    #print row
                    f.write("{r}\n".format(r=row))
            #------------------------------------------------------------        

            #------------------------------------------------------------
            # these timings are measured from simulation start!
            head = "CU_ID; New; exestart; exeEnd; Done; Cycle; Run"
            #print head
            f.write("{row}\n".format(row=head))

            for cycle in cu_performance_data:
                for run in cu_performance_data[cycle].keys():
                    for cid in cu_performance_data[cycle][run].keys():
                        cu = cu_performance_data[cycle][run][cid]
                        st_data = {}
                        for st in cu.state_history:
                            st_dict = st.as_dict()
                            st_data["{0}".format( st_dict["state"] )] = {}
                            st_data["{0}".format( st_dict["state"] )] = st_dict["timestamp"]

                        row = "{uid}; {New}; {exestart}; {exestop}; {Done}; {Cycle}; {Run}".format(
                            uid=cu.uid,
                            New=(st_data['Scheduling']-start).total_seconds(),
                            exestart=(cu.start_time-start).total_seconds(),
                            exestop=(cu.stop_time-start).total_seconds(),
                            Done=(st_data['Done']-start).total_seconds(),
                            Cycle=cycle,
                            Run=run)

                        #print row
                        f.write("{r}\n".format(r=row))


