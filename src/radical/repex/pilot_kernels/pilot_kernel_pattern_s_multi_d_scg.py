"""
.. module:: radical.repex.pilot_kernels.pilot_kernel_pattern_s_multi_d_sc
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

#-------------------------------------------------------------------------------

class PilotKernelPatternSmultiDscg(PilotKernel):
    """
    """
    def __init__(self, inp_file, rconfig):
        """Constructor.

        Arguments:
        inp_file - json input file with Pilot and NAMD related parameters as 
        specified by user 
        """
        PilotKernel.__init__(self, inp_file, rconfig)

        self.name = 'exec-pattern-A-multiDsc'
        self.logger  = rul.get_logger ('radical.repex', self.name)

        self.sd_shared_list = []

#-------------------------------------------------------------------------------

    def run_simulation(self, replicas, md_kernel):
        """This function runs the main loop of RE simulation for RE pattern B.

        Arguments:
        replicas - list of Replica objects
        md_kernel - an instance of NamdKernelScheme2a class
        """

        # ----------------------------------------------------------------------
        #
        def unit_state_change_cb(unit, state):

            if unit:            
                self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )

                if state == radical.pilot.states.FAILED:
                    self.logger.error("Log: {0:s}".format( unit.as_dict() ) )
                    # restarting the replica
                    #self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )
                    #unit_manager.submit_units( unit.description )

        #-----------------------------------------------------------------------
        cycles = md_kernel.nr_cycles
                
        unit_manager = radical.pilot.UnitManager(self.session, scheduler=radical.pilot.SCHED_DIRECT_SUBMISSION)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(self.pilot_object)

        stagein_start = datetime.datetime.utcnow()

        # staging shared input data in
        md_kernel.prepare_shared_data(replicas)

        shared_input_file_urls = md_kernel.shared_urls
        shared_input_files = md_kernel.shared_files

        for i,j in enumerate(shared_input_files):

            sd_pilot = {'source': shared_input_file_urls[i],
                        'target': 'staging:///%s' % shared_input_files[i],
                        'action': radical.pilot.TRANSFER
            }

            self.pilot_object.stage_in(sd_pilot)

            sd_shared = {'source': 'staging:///%s' % shared_input_files[i],
                         'target': shared_input_files[i],
                         'action': radical.pilot.COPY
            }
            self.sd_shared_list.append(sd_shared)

        # for performance data collection
        hl_performance_data = {}
        cu_performance_data = {}

        do_profile = os.getenv('REPEX_PROFILING', '0')

        #md_kernel.init_matrices(replicas)

        stagein_end = datetime.datetime.utcnow()

        start = datetime.datetime.utcnow()
        #-----------------------------------------------------------------------
        # bulk_submission = 0: do sequential submission
        # bulk_submission = 1: do bulk_submission submission
        bulk_submission = 1
        dim_int = 0
        current_cycle = 0
        
        dim_count = md_kernel.nr_dims
        dim_str = []
        dim_str.append('')
        for i in range(dim_count):
            s = 'd' + str(i+1)
            dim_str.append(s)

        for c in range(1,cycles*dim_count+1):

            if dim_int < dim_count:
                dim_int = dim_int + 1
            else:
                dim_int = 1
                current_cycle += 1

            if dim_int == 1:
                cu_performance_data["cycle_{0}".format(current_cycle)] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)] = {}

            self.logger.info("Performing cycle: {0}".format(current_cycle) )
            
            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)] = {}

            self.logger.info("Dim {0}: preparing {1} replicas for MD run; cycle {2}".format(dim_int, md_kernel.replicas, current_cycle) )
            
            submitted_groups = []
            exchange_replicas = []
            
            #-------------------------------------------------------------------
            # sequential submission
            if not bulk_submission:
                pass
            #-------------------------------------------------------------------
            # bulk_submission submision
            else:
                
                md_prep_timing = 0.0
                md_sub_timing  = 0.0
                md_exec_timing = 0.0
                t1 = datetime.datetime.utcnow()
                all_groups = md_kernel.get_all_groups(dim_int, replicas)
                t2 = datetime.datetime.utcnow()
                md_prep_timing += (t2-t1).total_seconds()

                c_units = []
                for group in all_groups:
                    t1 = datetime.datetime.utcnow()
                    compute_group = md_kernel.prepare_group_for_md(current_cycle, dim_int, dim_str[dim_int], group, self.sd_shared_list)
                    c_units.append(compute_group)
                    t2 = datetime.datetime.utcnow()
                    md_prep_timing += (t2-t1).total_seconds()

                t1 = datetime.datetime.utcnow()
                submitted_groups += unit_manager.submit_units(c_units)
                t2 = datetime.datetime.utcnow()
                md_sub_timing += (t2-t1).total_seconds()

                t1 = datetime.datetime.utcnow()
                unit_manager.wait_units()
                t2 = datetime.datetime.utcnow()
                md_exec_timing += (t2-t1).total_seconds()

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_prep"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_prep"] = md_prep_timing

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_sub"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_sub"] = md_sub_timing

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_run"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_run"] = md_exec_timing

                #---------------------------------------------------------------
                t1 = datetime.datetime.utcnow()
                ex_calculator = md_kernel.prepare_global_ex_calc(current_cycle, dim_int, dim_str[dim_int], replicas, self.sd_shared_list)
                t2 = datetime.datetime.utcnow()

                t_1 = datetime.datetime.utcnow()
                global_ex_cu = unit_manager.submit_units(ex_calculator)
                t_2 = datetime.datetime.utcnow()

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_prep"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_prep"] = (t2-t1).total_seconds()

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_sub"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_sub"] = (t_2-t_1).total_seconds()
                #-----------------------------------------------------------

                t1 = datetime.datetime.utcnow()
                unit_manager.wait_units()
                t2 = datetime.datetime.utcnow()

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_run"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_run"] = (t2-t1).total_seconds()
            
            #-------------------------------------------------------------------

            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_run"] = {}
            for cu in submitted_groups:
                cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_run"]["cu.uid_{0}".format(cu.uid)] = cu
            
            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["global_ex_run"] = {}
            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["global_ex_run"]["cu.uid_{0}".format(global_ex_cu.uid)] = global_ex_cu

            #-------------------------------------------------------------------
            #               
            t1 = datetime.datetime.utcnow()
            for r in submitted_groups:
                if r.state != radical.pilot.DONE:
                    self.logger.error('ERROR: In D%d MD-step failed for unit:  %s' % (dim_int, r.uid))

            if len(exchange_replicas) > 0:
                for r in exchange_replicas:
                    if r.state != radical.pilot.DONE:
                        self.logger.error('ERROR: In D%d Exchange-step failed for unit:  %s' % (dim_int, r.uid))

            if global_ex_cu.state != radical.pilot.DONE:
                self.logger.error('ERROR: In D%d Global-Exchange-step failed for unit:  %s' % (dim_int, global_ex_cu.uid))

            # do exchange of parameters                     
            md_kernel.do_exchange(current_cycle, dim_int, dim_str[dim_int], replicas)
            t2 = datetime.datetime.utcnow()
                
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["post_proc"] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["post_proc"] = (t2-t1).total_seconds()
            
            #-------------------------------------------------------------------
            # performance data
            if do_profile == '1':
                outfile = "execution_profile_{mysession}.csv".format(mysession=self.session.uid)
                with open(outfile, 'a') as f:
                    
                    #---------------------------------------------------------------
                    #
                    head = "Cycle; Dim; Run; Duration"
                    f.write("{row}\n".format(row=head))

                    hl_cycle = "cycle_{0}".format(current_cycle)
                    hl_dim   = "dim_{0}".format(dim_int)
                    
                    for run in hl_performance_data[hl_cycle][hl_dim].keys():
                        dur = hl_performance_data[hl_cycle][hl_dim][run]

                        row = "{Cycle}; {Dim}; {Run}; {Duration}".format(
                            Duration=dur,
                            Cycle=hl_cycle,
                            Dim=hl_dim,
                            Run=run)

                        f.write("{r}\n".format(r=row))

                    #---------------------------------------------------------------
                    head = "CU_ID; Scheduling; StagingInput; AgentStagingInput; Allocating; Executing; StagingOutput; Done; Cycle; Dim; Run;"
                    f.write("{row}\n".format(row=head))
                   
                    for run in cu_performance_data[hl_cycle][hl_dim].keys():
                        for cid in cu_performance_data[hl_cycle][hl_dim][run].keys():
                            cu = cu_performance_data[hl_cycle][hl_dim][run][cid]
                            st_data = {}
                            for st in cu.state_history:
                                st_dict = st.as_dict()
                                st_data["{0}".format( st_dict["state"] )] = {}
                                st_data["{0}".format( st_dict["state"] )] = st_dict["timestamp"]
                           
                            row = "{uid}; {Scheduling}; {StagingInput}; {AgentStagingInput}; {Allocating}; {Executing}; {StagingOutput}; {Done}; {Cycle}; {Dim}; {Run}".format(
                                uid=cu.uid,
                                #Unscheduled=st_data['Unscheduled'],
                                Scheduling=st_data['Scheduling'],
                                #PendingInputStaging = st_data['PendingInputStaging'],
                                StagingInput=st_data['StagingInput'],
                                #PendingAgentInputStaging=st_data['PendingAgentInputStaging'],
                                AgentStagingInput=st_data['AgentStagingInput'],
                                #PendingExecution=st_data['PendingExecution'],
                                Allocating=st_data['Allocating'],
                                Executing=st_data['Executing'],
                                #PendingAgentOutputStaging=st_data['PendingAgentOutputStaging'],
                                #AgentStagingOutput=st_data['AgentStagingOutput'],
                                #PendingOutputStaging=st_data['PendingOutputStaging'],
                                StagingOutput=st_data['StagingOutput'],
                                Done=st_data['Done'],
                                Cycle=hl_cycle,
                                Dim=hl_dim,
                                Run=run)

                            f.write("{r}\n".format(r=row))
            
        #-----------------------------------------------------------------------
        # end of loop
        if do_profile == '1':
            outfile = "execution_profile_{mysession}.csv".format(mysession=self.session.uid)
            with open(outfile, 'a') as f:
                # RAW SIMULATION TIME
                end = datetime.datetime.utcnow()
                stagein_time = (stagein_end-stagein_start).total_seconds()
                raw_simulation_time = (end-start).total_seconds()
                f.write("Total simulaiton time: {row}\n".format(row=raw_simulation_time))
                f.write("Stage-in time: {row}\n".format(row=stagein_time))

