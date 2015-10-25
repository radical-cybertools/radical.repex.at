"""
.. module:: radical.repex.pilot_kernels.pilot_kernel_pattern_a_multi_d
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
from pilot_kernels.pilot_kernel import *
import radical.utils.logger as rul

#-------------------------------------------------------------------------------

class PilotKernelPatternSmultiD(PilotKernel):
   
    def __init__(self, inp_file, rconfig):
        """Constructor.

        Arguments:
        inp_file - json input file with Pilot and NAMD related parameters as 
        specified by user 
        """
        PilotKernel.__init__(self, inp_file, rconfig)

        self.name = 'exec-pattern-A-multiD'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        self.sd_shared_list = []

#-------------------------------------------------------------------------------

    def run_simulation(self, replicas, pilot_object, session,  md_kernel):
        """This function runs the main loop of RE simulation for RE pattern B.

        Arguments:
        replicas - list of Replica objects
        pilot_object - radical.pilot.ComputePilot object
        session - radical.pilot.session object, the *root* object for all other 
        RADICAL-Pilot objects 
        md_kernel - an instance of NamdKernelScheme2a class
        """

        # ----------------------------------------------------------------------
        #
        def unit_state_change_cb(unit, state):
            """This is a callback function. It gets called very time a 
            ComputeUnit changes its state.
            """

            if unit:            
                self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )

                if state == radical.pilot.states.FAILED:
                    self.logger.error("Log: {0:s}".format( unit.as_dict() ) )
                    # restarting the replica
                    #self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )
                    #unit_manager.submit_units( unit.description )

        # ----------------------------------------------------------------------
        cycles = md_kernel.nr_cycles + 1
                
        unit_manager = radical.pilot.UnitManager(session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(pilot_object)

        stagein_start = datetime.datetime.utcnow()

        # staging shared input data in
        md_kernel.prepare_shared_data(replicas)

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

        # for performance data collection
        hl_performance_data = {}
        cu_performance_data = {}

        do_profile = os.getenv('REPEX_PROFILING', '0')

        md_kernel.init_matrices(replicas)

        stagein_end = datetime.datetime.utcnow()

        start = datetime.datetime.utcnow()
        #------------------------
        # GL = 0: submit global calculator before
        # GL = 1: submit global calculator after
        GL = 1
        # BULK = 0: do sequential submission
        # BULK = 1: do BULK submission
        BULK = 1
        DIM = 0
        dimensions = md_kernel.dims
        for c in range(0,cycles*dimensions):

            if DIM < dimensions:
                DIM = DIM + 1
            else:
                DIM = 1

            current_cycle = c / dimensions

            if DIM == 1:
                cu_performance_data["cycle_{0}".format(current_cycle)] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)] = {}

            self.logger.info("Performing cycle: {0}".format(current_cycle) )
            
            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)] = {}

            self.logger.info("Dim {0}: preparing {1} replicas for MD run; cycle {2}".format(DIM, md_kernel.replicas, current_cycle) )
            
            submitted_replicas = []
            exchange_replicas = []
            
            #-------------------------------------------------------------------
            # sequential submission
            if BULK == 0:

                #---------------------------------------------------------------
                # submitting unit which determines exchanges between replicas
                if GL == 0:
                    ex_calculator = md_kernel.prepare_global_ex_calc(GL, current_cycle, DIM, replicas, self.sd_shared_list)
                    global_ex_cu = unit_manager.submit_units(ex_calculator)
                #---------------------------------------------------------------

                t1 = datetime.datetime.utcnow()
                for replica in replicas:
                    compute_replica = md_kernel.prepare_replica_for_md(DIM, replicas, replica, self.sd_shared_list)
                    sub_replica = unit_manager.submit_units(compute_replica)
                    submitted_replicas.append(sub_replica)
                t2 = datetime.datetime.utcnow()

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["md_prep"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["md_prep"] = (t2-t1).total_seconds()

                if (DIM == 2) and (md_kernel.d2 == 'salt_concentration'):
                    t1 = datetime.datetime.utcnow()
                    unit_manager.wait_units()
                    t2 = datetime.datetime.utcnow()

                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["md_run"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["md_run"] = (t2-t1).total_seconds()

                    t1 = datetime.datetime.utcnow()
                    for replica in replicas:
                        ex_replica = md_kernel.prepare_replica_for_exchange(DIM, replicas, replica, self.sd_shared_list)
                        sub_replica = unit_manager.submit_units(ex_replica)
                        exchange_replicas.append(sub_replica)
                    t2 = datetime.datetime.utcnow()
                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["ex_prep_salt"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["ex_prep_salt"] = (t2-t1).total_seconds()
                    
                    #-----------------------------------------------------------
                    # submitting unit which determines exchanges between replicas
                    if GL == 1:
                        ex_calculator = md_kernel.prepare_global_ex_calc(GL, current_cycle, DIM, replicas, self.sd_shared_list)
                        global_ex_cu = unit_manager.submit_units(ex_calculator)
                    #-----------------------------------------------------------

                    t1 = datetime.datetime.utcnow()
                    unit_manager.wait_units()
                    t2 = datetime.datetime.utcnow()

                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["ex_run_salt"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["ex_run_salt"] = (t2-t1).total_seconds()
                
                if (DIM != 2) or (md_kernel.d2 != 'salt_concentration'):

                    #-----------------------------------------------------------
                    # submitting unit which determines exchanges between replicas
                    if GL == 1:
                        ex_calculator = md_kernel.prepare_global_ex_calc(GL, current_cycle, DIM, replicas, self.sd_shared_list)
                        global_ex_cu = unit_manager.submit_units(ex_calculator)
                    #-----------------------------------------------------------

                    t1 = datetime.datetime.utcnow()
                    unit_manager.wait_units()
                    t2 = datetime.datetime.utcnow()

                    # md run includes timings for global calc since there isn't
                    # a separate set of CU's for exchange!
                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["md_run"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["md_run"] = (t2-t1).total_seconds()
                else:
                    unit_manager.wait_units()
            #-------------------------------------------------------------------
            # BULK submision
            else:

                #---------------------------------------------------------------
                # submitting unit which determines exchanges between replicas
                if GL == 0:
                    ex_calculator = md_kernel.prepare_global_ex_calc(GL, current_cycle, DIM, replicas, self.sd_shared_list)
                    global_ex_cu = unit_manager.submit_units(ex_calculator)
                #---------------------------------------------------------------
                
                c_replicas = []
                t1 = datetime.datetime.utcnow()
                for replica in replicas:
                    # DIM, replicas, replica, self.sd_shared_list
                    compute_replica = md_kernel.prepare_replica_for_md(DIM, replicas, replica, self.sd_shared_list)
                    c_replicas.append(compute_replica)
                t2 = datetime.datetime.utcnow()
                submitted_replicas = unit_manager.submit_units(c_replicas)

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["md_prep"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["md_prep"] = (t2-t1).total_seconds()

                #---------------------------------------------------------------
                
                e_replicas = []
                if (DIM == 2) and (md_kernel.d2 == 'salt_concentration'):
                    t1 = datetime.datetime.utcnow()
                    unit_manager.wait_units()
                    t2 = datetime.datetime.utcnow()

                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["md_run"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["md_run"] = (t2-t1).total_seconds()

                    t1 = datetime.datetime.utcnow()
                    for replica in replicas:
                        ex_replica = md_kernel.prepare_replica_for_exchange(DIM, replicas, replica, self.sd_shared_list)
                        e_replicas.append(ex_replica)
                    exchange_replicas = unit_manager.submit_units(e_replicas) 
                    t2 = datetime.datetime.utcnow()

                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["ex_prep_salt"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["ex_prep_salt"] = (t2-t1).total_seconds()

                    #-----------------------------------------------------------
                    # submitting unit which determines exchanges between replicas
                    if GL == 1:
                        ex_calculator = md_kernel.prepare_global_ex_calc(GL, current_cycle, DIM, replicas, self.sd_shared_list)
                        global_ex_cu = unit_manager.submit_units(ex_calculator)
                    #-----------------------------------------------------------
                    
                    t1 = datetime.datetime.utcnow()
                    unit_manager.wait_units()
                    t2 = datetime.datetime.utcnow()

                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["ex_run_salt"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["ex_run_salt"] = (t2-t1).total_seconds()
                
                
                if (DIM != 2) or (md_kernel.d2 != 'salt_concentration'):
                    #-----------------------------------------------------------
                    # submitting unit which determines exchanges between replicas
                    if GL == 1:
                        ex_calculator = md_kernel.prepare_global_ex_calc(GL, current_cycle, DIM, replicas, self.sd_shared_list)
                        global_ex_cu = unit_manager.submit_units(ex_calculator)
                    #-----------------------------------------------------------

                    t1 = datetime.datetime.utcnow()
                    unit_manager.wait_units()
                    t2 = datetime.datetime.utcnow()

                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["md_run"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["md_run"] = (t2-t1).total_seconds()
                else:
                    unit_manager.wait_units()
            #-------------------------------------------------------------------

            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["run_{0}".format("MD")] = {}
            for cu in submitted_replicas:
                cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["run_{0}".format("MD")]["cu.uid_{0}".format(cu.uid)] = cu
            
            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["run_{0}".format("EX_salt")] = {}
            for cu in exchange_replicas:
                cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["run_{0}".format("EX_salt")]["cu.uid_{0}".format(cu.uid)] = cu

            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["run_{0}".format("GLOBAL_EX")] = {}
            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["run_{0}".format("GLOBAL_EX")]["cu.uid_{0}".format(global_ex_cu.uid)] = global_ex_cu

            #-------------------------------------------------------------------
            #               
            t1 = datetime.datetime.utcnow()
            for r in submitted_replicas:
                if r.state != radical.pilot.DONE:
                    self.logger.error('ERROR: In D%d MD-step failed for unit:  %s' % (DIM, r.uid))

            if len(exchange_replicas) > 0:
                for r in exchange_replicas:
                    if r.state != radical.pilot.DONE:
                        self.logger.error('ERROR: In D%d Exchange-step failed for unit:  %s' % (DIM, r.uid))

            if global_ex_cu.state != radical.pilot.DONE:
                self.logger.error('ERROR: In D%d Global-Exchange-step failed for unit:  %s' % (DIM, global_ex_cu.uid))

            # do exchange of parameters                     
            md_kernel.do_exchange(current_cycle, DIM, replicas)
            t2 = datetime.datetime.utcnow()
                
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["POST_PROC"] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(DIM)]["POST_PROC"] = (t2-t1).total_seconds()
            
            #-------------------------------------------------------------------
            # performance data
            if do_profile == '1':
                outfile = "execution_profile_{mysession}.csv".format(mysession=session.uid)
                with open(outfile, 'a') as f:
                    
                    #-----------------------------------------------------------
                    #
                    head = "Cycle; Dim; Run; Duration"
                    f.write("{row}\n".format(row=head))

                    hl_cycle = "cycle_{0}".format(current_cycle)
                    hl_dim   = "dim_{0}".format(DIM)
                    
                    for run in hl_performance_data[hl_cycle][hl_dim].keys():
                        dur = hl_performance_data[hl_cycle][hl_dim][run]

                        row = "{Cycle}; {Dim}; {Run}; {Duration}".format(
                            Duration=dur,
                            Cycle=hl_cycle,
                            Dim=hl_dim,
                            Run=run)

                        f.write("{r}\n".format(r=row))

                    #-----------------------------------------------------------
                    head = "CU_ID; Scheduling; StagingInput; PendingAgentInputStaging; AgentStagingInput; Allocating; Executing; PendingAgentOutputStaging; PendingOutputStaging; StagingOutput; Done; Cycle; Dim; Run;"
                    f.write("{row}\n".format(row=head))
                   
                    for run in cu_performance_data[hl_cycle][hl_dim].keys():
                        for cid in cu_performance_data[hl_cycle][hl_dim][run].keys():
                            cu = cu_performance_data[hl_cycle][hl_dim][run][cid]
                            st_data = {}
                            for st in cu.state_history:
                                st_dict = st.as_dict()
                                st_data["{0}".format( st_dict["state"] )] = {}
                                st_data["{0}".format( st_dict["state"] )] = st_dict["timestamp"]
                           
                            row = "{uid}; {Scheduling}; {StagingInput}; {PendingAgentInputStaging}; {AgentStagingInput}; {Allocating}; {Executing}; {PendingAgentOutputStaging}; {PendingOutputStaging}; {StagingOutput}; {Done}; {Cycle}; {Dim}; {Run}".format(
                                uid=cu.uid,
                                #Unscheduled=st_data['Unscheduled'],
                                Scheduling=st_data['Scheduling'],
                                #PendingInputStaging = st_data['PendingInputStaging'],
                                StagingInput=st_data['StagingInput'],
                                PendingAgentInputStaging=st_data['PendingAgentInputStaging'],
                                AgentStagingInput=st_data['AgentStagingInput'],
                                #PendingExecution=st_data['PendingExecution'],
                                Allocating=st_data['Allocating'],
                                Executing=st_data['Executing'],
                                PendingAgentOutputStaging=st_data['PendingAgentOutputStaging'],
                                #AgentStagingOutput=st_data['AgentStagingOutput'],
                                PendingOutputStaging=st_data['PendingOutputStaging'],
                                StagingOutput=st_data['StagingOutput'],
                                Done=st_data['Done'],
                                Cycle=hl_cycle,
                                Dim=hl_dim,
                                Run=run)

                            f.write("{r}\n".format(r=row))
            
        #-----------------------------------------------------------------------
        # end of loop

        if do_profile == '1':
            outfile = "execution_profile_{mysession}.csv".format(mysession=session.uid)
            with open(outfile, 'a') as f:
                # RAW SIMULATION TIME
                end = datetime.datetime.utcnow()
                stagein_time = (stagein_end-stagein_start).total_seconds()
                raw_simulation_time = (end-start).total_seconds()
                f.write("Total simulaiton time: {row}\n".format(row=raw_simulation_time))
                f.write("Stage-in time: {row}\n".format(row=stagein_time))

