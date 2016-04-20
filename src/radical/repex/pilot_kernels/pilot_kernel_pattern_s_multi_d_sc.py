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

class PilotKernelPatternSmultiDsc(PilotKernel):
    """
    """
    def __init__(self, inp_file, rconfig):
        """
        Arguments:
        inp_file - json input file with Pilot and NAMD related parameters as 
        specified by user 
        """
        PilotKernel.__init__(self, inp_file, rconfig)

        self.name = 'exec-pattern-A-multiDsc'
        self.logger  = rul.getLogger ('radical.repex', self.name)

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
        cycles = md_kernel.nr_cycles + 1
                
        unit_manager = radical.pilot.UnitManager(self.session, scheduler=radical.pilot.SCHED_DIRECT_SUBMISSION)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(self.pilot_object)

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

        if md_kernel.restart == True:
            dim_int = md_kernel.restart_object.dimension
        else:
            dim_int = 0

        dim_count = md_kernel.nr_dims
        dim_str = []
        dim_str.append('')
        for i in range(dim_count):
            s = 'd' + str(i+1)
            dim_str.append(s)

        for c in range(0,cycles*dim_count):

            if dim_int < dim_count:
                dim_int = dim_int + 1
            else:
                dim_int = 1
            current_cycle = c / dim_count

            if dim_int == 1:
                cu_performance_data["cycle_{0}".format(current_cycle)] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)] = {}

            self.logger.info("Performing cycle: {0}".format(current_cycle) )
            
            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)] = {}

            self.logger.info("dim_int {0}: preparing {1} replicas for MD run; cycle {2}".format(dim_int, md_kernel.replicas, current_cycle) )
            
            submitted_replicas = []
            exchange_replicas = []
            
            #-------------------------------------------------------------------
            #
            if bulk_submission:
                
                md_prep_timing = 0.0
                md_sub_timing  = 0.0
                md_exec_timing = 0.0
                t1 = datetime.datetime.utcnow()
                all_groups = md_kernel.get_all_groups(dim_int, replicas)

                for group in all_groups:
                    group.pop(0)

                t2 = datetime.datetime.utcnow()
                md_prep_timing += (t2-t1).total_seconds()

                batch = []
                r_cores = md_kernel.replica_cores
                for group in all_groups:
                    # assumes uniform distribution of cores
                    if ( (len(batch)+len(group))*r_cores ) <= self.cores:
                        batch += group
                    else:
                        if len(batch) == 0:
                            self.logger.error('ERROR: batch is empty, no replicas to prepare!')
                            sys.exit(1)

                        t1 = datetime.datetime.utcnow()
                        c_replicas = []
                        for replica in batch:
                            compute_replica = md_kernel.prepare_replica_for_md(dim_int, dim_str[dim_int], replicas, replica, self.sd_shared_list)
                            c_replicas.append(compute_replica)
                        t2 = datetime.datetime.utcnow()
                        md_prep_timing += (t2-t1).total_seconds()

                        t1 = datetime.datetime.utcnow()
                        submitted_batch = unit_manager.submit_units(c_replicas)
                        submitted_replicas += submitted_batch
                        t2 = datetime.datetime.utcnow()
                        md_sub_timing += (t2-t1).total_seconds()

                        unit_ids = []
                        for item in submitted_batch:
                            unit_ids.append( item.uid )
                        t1 = datetime.datetime.utcnow()
                        unit_manager.wait_units( unit_ids=unit_ids)
                        t2 = datetime.datetime.utcnow()
                        md_exec_timing += (t2-t1).total_seconds()
                        batch = []
                        batch += group
                if len(batch) != 0:
                    t1 = datetime.datetime.utcnow()
                    c_replicas = []
                    for replica in batch:
                        compute_replica = md_kernel.prepare_replica_for_md(dim_int, dim_str[dim_int], replicas, replica, self.sd_shared_list)
                        c_replicas.append(compute_replica)
                    t2 = datetime.datetime.utcnow()
                    md_prep_timing += (t2-t1).total_seconds()

                    t1 = datetime.datetime.utcnow()
                    submitted_batch = unit_manager.submit_units(c_replicas)
                    submitted_replicas += submitted_batch
                    t2 = datetime.datetime.utcnow()
                    md_sub_timing += (t2-t1).total_seconds()
                    
                    unit_ids = []
                    for item in submitted_batch:
                        unit_ids.append( item.uid )    
                    t1 = datetime.datetime.utcnow()
                    unit_manager.wait_units( unit_ids=unit_ids)
                    t2 = datetime.datetime.utcnow()
                    md_exec_timing += (t2-t1).total_seconds()

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_prep"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_prep"] = md_prep_timing

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_sub"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_sub"] = md_sub_timing

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_run"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_run"] = md_exec_timing

                #---------------------------------------------------------------
                #
                if (md_kernel.dims[dim_str[dim_int]]['type'] == 'salt'):

                    ex_prep_timing = 0.0
                    ex_sub_timing  = 0.0
                    ex_exec_timing = 0.0
                    t1 = datetime.datetime.utcnow()
                    all_groups = md_kernel.get_all_groups(dim_int, replicas)
                    t2 = datetime.datetime.utcnow()
                    ex_prep_timing += (t2-t1).total_seconds()

                    for group in all_groups:
                        group.pop(0)

                    batch = []
                    r_cores = md_kernel.dims[dim_str[dim_int]]['replicas']
                    for group in all_groups:
                        if ( (len(batch)+len(group))*r_cores ) <= self.cores:
                            batch += group
                        else:
                            if len(batch) == 0:
                                self.logger.error('ERROR: batch is empty, no replicas to prepare!')
                                sys.exit(1)

                            t1 = datetime.datetime.utcnow()
                            e_replicas = []
                            for replica in batch:
                                ex_replica = md_kernel.prepare_replica_for_exchange(dim_int, dim_str[dim_int], replicas, replica, self.sd_shared_list)
                                e_replicas.append(ex_replica)
                            t2 = datetime.datetime.utcnow()
                            ex_prep_timing += (t2-t1).total_seconds()

                            t1 = datetime.datetime.utcnow()
                            exchange_replicas += unit_manager.submit_units(e_replicas) 
                            t2 = datetime.datetime.utcnow()
                            ex_sub_timing += (t2-t1).total_seconds()

                            t1 = datetime.datetime.utcnow()
                            unit_manager.wait_units()
                            t2 = datetime.datetime.utcnow()
                            ex_exec_timing += (t2-t1).total_seconds()
                            batch = []
                            batch += group
                    if len(batch) != 0:
                        t1 = datetime.datetime.utcnow()
                        e_replicas = []
                        for replica in batch:
                            ex_replica = md_kernel.prepare_replica_for_exchange(dim_int, dim_str[dim_int], replicas, replica, self.sd_shared_list)
                            e_replicas.append(ex_replica)
                        t2 = datetime.datetime.utcnow()
                        ex_prep_timing += (t2-t1).total_seconds()

                        t1 = datetime.datetime.utcnow()
                        exchange_replicas += unit_manager.submit_units(e_replicas) 
                        t2 = datetime.datetime.utcnow()
                        ex_sub_timing += (t2-t1).total_seconds()

                        t1 = datetime.datetime.utcnow()
                        unit_manager.wait_units()
                        t2 = datetime.datetime.utcnow()
                        ex_exec_timing += (t2-t1).total_seconds()

                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_prep_salt"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_prep_salt"] = ex_prep_timing

                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_sub_salt"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_sub_salt"] = ex_sub_timing

                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_run_salt"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_run_salt"] = ex_exec_timing

                    #-----------------------------------------------------------
                    # submitting unit which determines exchanges between replicas
                  
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
                
                else:
                    #-----------------------------------------------------------
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
                    unit_manager.wait_units( unit_ids=global_ex_cu.uid )
                    t2 = datetime.datetime.utcnow()

                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_run"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_run"] = (t2-t1).total_seconds()
                
            #-------------------------------------------------------------------

            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_run"] = {}
            for cu in submitted_replicas:
                cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["md_run"]["cu.uid_{0}".format(cu.uid)] = cu
            
            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_run_salt"] = {}
            for cu in exchange_replicas:
                cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["ex_run_salt"]["cu.uid_{0}".format(cu.uid)] = cu

            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["global_ex_run"] = {}
            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["global_ex_run"]["cu.uid_{0}".format(global_ex_cu.uid)] = global_ex_cu

            #-------------------------------------------------------------------
            # 
            failed_cus = []              
            t1 = datetime.datetime.utcnow()
            for r in submitted_replicas:
                if r.state != radical.pilot.DONE:
                    self.logger.error('ERROR: In D%d MD-step failed for unit:  %s' % (dim_int, r.uid))
                    failed_cus.append( r.uid )

            if len(exchange_replicas) > 0:
                for r in exchange_replicas:
                    if r.state != radical.pilot.DONE:
                        self.logger.error('ERROR: In D%d Exchange-step failed for unit:  %s' % (dim_int, r.uid))
                        failed_cus.append( r.uid )

            if global_ex_cu.state != radical.pilot.DONE:
                self.logger.error('ERROR: In D%d Global-Exchange-step failed for unit:  %s' % (dim_int, global_ex_cu.uid))
                failed_cus.append( global_ex_cu.uid )

            # do exchange of parameters                     
            md_kernel.do_exchange(current_cycle, dim_int, dim_str[dim_int], replicas)
            t2 = datetime.datetime.utcnow()
                
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["post_proc"] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(dim_int)]["post_proc"] = (t2-t1).total_seconds()
            
            #write replica objects out
            md_kernel.save_replicas(current_cycle, dim_int, dim_str[dim_int], replicas)

            #-------------------------------------------------------------------
            # performance data
            if do_profile == '1':
                outfile = "execution_profile_{mysession}.csv".format(mysession=self.session.uid)
                with open(outfile, 'a') as f:
                    
                    #-----------------------------------------------------------
                    #
                    head = "Cycle; dim_int; Run; Duration"
                    f.write("{row}\n".format(row=head))

                    hl_cycle = "cycle_{0}".format(current_cycle)
                    hl_dim   = "dim_{0}".format(dim_int)
                    
                    for run in hl_performance_data[hl_cycle][hl_dim].keys():
                        dur = hl_performance_data[hl_cycle][hl_dim][run]

                        row = "{Cycle}; {dim_int}; {Run}; {Duration}".format(
                            Duration=dur,
                            Cycle=hl_cycle,
                            dim_int=hl_dim,
                            Run=run)

                        f.write("{r}\n".format(r=row))

                    #-----------------------------------------------------------
                    head = "CU_ID; Scheduling; StagingInput; AgentStagingInput; Allocating; Executing; StagingOutput; Done; Cycle; dim_int; Run;"
                    f.write("{row}\n".format(row=head))
                   
                    for run in cu_performance_data[hl_cycle][hl_dim].keys():
                        for cid in cu_performance_data[hl_cycle][hl_dim][run].keys():
                            cu = cu_performance_data[hl_cycle][hl_dim][run][cid]
                            if cu.uid not in failed_cus:
                                st_data = {}
                                for st in cu.state_history:
                                    st_dict = st.as_dict()
                                    st_data["{0}".format( st_dict["state"] )] = {}
                                    st_data["{0}".format( st_dict["state"] )] = st_dict["timestamp"]
                               
                                row = "{uid}; {Scheduling}; {StagingInput}; {AgentStagingInput}; {Allocating}; {Executing}; {StagingOutput}; {Done}; {Cycle}; {dim_int}; {Run}".format(
                                    uid=cu.uid,
                                    Scheduling=st_data['Scheduling'],
                                    StagingInput=st_data['StagingInput'],
                                    AgentStagingInput=st_data['AgentStagingInput'],
                                    Allocating=st_data['Allocating'],
                                    Executing=st_data['Executing'],
                                    StagingOutput=st_data['StagingOutput'],
                                    Done=st_data['Done'],
                                    Cycle=hl_cycle,
                                    dim_int=hl_dim,
                                    Run=run)

                            f.write("{r}\n".format(r=row))
            
        #-----------------------------------------------------------------------
        # end of loop
        if do_profile == '1':
            outfile = "execution_profile_{mysession}.csv".format(mysession=self.session.uid)
            with open(outfile, 'a') as f:
                end = datetime.datetime.utcnow()
                stagein_time = (stagein_end-stagein_start).total_seconds()
                raw_simulation_time = (end-start).total_seconds()
                f.write("Total simulaiton time: {row}\n".format(row=raw_simulation_time))
                f.write("Stage-in time: {row}\n".format(row=stagein_time))

