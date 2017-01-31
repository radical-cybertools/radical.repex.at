"""
.. module:: radical.repex.execution_management_modules.exec_mng_module_pattern_s
.. moduleauthor::  <antons.treikalis@gmail.com>
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
import radical.pilot as rp
import radical.utils as ru
import radical.utils.logger as rul
from execution_management_modules.exec_mng_module import *

#-------------------------------------------------------------------------------

class ExecutionManagementModulePatternS(ExecutionManagementModule):
    """Execution Management Module for synchronous RE pattern. This module 
    can be used by any AMM.

    Attributes:
        name - name of this EMM

        sd_shared_list - list with RP's data directoves for staging of 
        simulation input files, from staging area to CU's workdir
    """

    def __init__(self, inp_file, rconfig, md_logger):
        """
        Args:
            inp_file - simulation input file with parameters specified by user 

            rconfig  - resource configuration file
            
            md_logger - logger of associated AMM 
        """

        ExecutionManagementModule.__init__(self, inp_file, rconfig, md_logger)

        self.name   = 'EMMpatternS'
        self.sd_shared_list = []

#-------------------------------------------------------------------------------

    def run_simulation(self, replicas, md_kernel):
        """Runs the main loop of synchronous RE simulation. Profiling probes are
        inserted here.

        Args:
            replicas - list of Replica objects

            md_kernel - an instance of AMM
        """

        #-----------------------------------------------------------------------
        #
        def unit_state_change_cb(unit, state):
            """Callback function. It gets called every time a CU changes its 
            state.
            """
            if unit:            
                self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )

                if state == rp.states.FAILED:
                    self.logger.info("Log: {0:s}".format( unit.as_dict() ) )
                    # restar replica here
                    
        #-----------------------------------------------------------------------

        self._prof.prof('run_simulation_start')

        cycles = md_kernel.nr_cycles
                
        unit_manager = rp.UnitManager(self.session, scheduler=rp.SCHED_DIRECT_SUBMISSION)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(self.pilot_object)

        self._prof.prof('initial_stagein_start')

        # staging shared input data in
        md_kernel.prepare_shared_data(replicas)

        shared_input_file_urls = md_kernel.shared_urls
        shared_input_files = md_kernel.shared_files

        for i,j in enumerate(shared_input_files):

            sd_pilot = {'source': shared_input_file_urls[i],
                        'target': 'staging:///%s' % shared_input_files[i],
                        'action': rp.TRANSFER
            }

            self.pilot_object.stage_in(sd_pilot)

            sd_shared = {'source': 'staging:///%s' % shared_input_files[i],
                         'target': shared_input_files[i],
                         'action': rp.COPY
            }
            self.sd_shared_list.append(sd_shared)

        self._prof.prof('initial_stagein_end')

        #-----------------------------------------------------------------------
        # bulk_submission = 0: do sequential submission
        # bulk_submission = 1: do bulk_submission submission
        bulk_submission = 1

        if md_kernel.restart == True:
            dim_int = md_kernel.restart_object.dimension
            current_cycle = md_kernel.restart_object.current_cycle
        else:
            dim_int = 0
            current_cycle = 1

        dim_count = md_kernel.nr_dims
        dim_str = []
        dim_str.append('')
        for i in range(dim_count):
            s = 'd' + str(i+1)
            dim_str.append(s)

        #-----------------------------------------------------------------------
        self._prof.prof('main_simulation_loop_start')
        for c in range(1,cycles*dim_count+1):

            if dim_int < dim_count:
                dim_int = dim_int + 1
            else:
                dim_int = 1
                current_cycle += 1

            self.logger.info("parameters before exchange: ")
            for r in replicas:
                self.logger.info("replica: {0} type: {1} param: {2}".format(r.id, r.dims[dim_str[dim_int]]['type'], r.dims[dim_str[dim_int]]['par']) )

            self.logger.info("performing cycle: {0} c: {1}".format(current_cycle, c) )
            
            submitted_replicas = []
            exchange_replicas = []

            c_str = '_c' + str(current_cycle) + '_d' + str(dim_int)
            #-------------------------------------------------------------------
            #
            if bulk_submission:
                
                md_prep_timing = 0.0
                md_sub_timing  = 0.0
                md_exec_timing = 0.0
                self._prof.prof('get_all_groups_start__' + c_str)
                all_groups = md_kernel.get_all_groups(dim_int, replicas)

                for group in all_groups:
                    group.pop(0)
                self._prof.prof('get_all_groups_end__' + c_str)

                batch = []
                r_cores = md_kernel.replica_cores
                for group in all_groups:
                    # assumes uniform distribution of cores
                    if ( (len(batch)+len(group))*r_cores ) <= self.cores:
                        batch.append(group)
                    else:
                        # we have more replicas than cores in a single group
                        if len(batch) == 0 and len(group) > self.cores:
                            batch.append(group)
                        elif len(batch) == 0:
                            self.logger.info('ERROR: batch is empty, no replicas to prepare!')
                            sys.exit(1)

                        c_replicas = []
                        self._prof.prof('prepare_replica_for_md_start__' + c_str )
                        for group in batch:
                            for replica in group:
                                compute_replica = md_kernel.prepare_replica_for_md(current_cycle, dim_int, dim_str[dim_int], group, replica, self.sd_shared_list)
                                c_replicas.append(compute_replica)
                        self._prof.prof('prepare_replica_for_md_end__' + c_str )

                        self._prof.prof('submit_md_units_start__' + c_str )
                        submitted_batch = unit_manager.submit_units(c_replicas)
                        self._prof.prof('submit_md_units_end__' + c_str )

                        submitted_replicas += submitted_batch

                        unit_ids = []
                        for item in submitted_batch:
                            unit_ids.append( item.uid )

                        self._prof.prof('wait_md_units_start__' + c_str )
                        unit_manager.wait_units( unit_ids=unit_ids)
                        self._prof.prof('wait_md_units_end__' + c_str )

                        if len(group) < self.cores:
                            batch = []
                            batch.append(group)
                        else:
                            batch = []

                if len(batch) != 0:
                    c_replicas = []
                    self._prof.prof('prepare_replica_for_md_start__' + c_str )
                    for group in batch:
                        for replica in group:
                            compute_replica = md_kernel.prepare_replica_for_md(current_cycle, dim_int, dim_str[dim_int], group, replica, self.sd_shared_list)
                            c_replicas.append(compute_replica)
                    self._prof.prof('prepare_replica_for_md_end__' + c_str )

                    self._prof.prof('submit_md_units_start__' + c_str )
                    submitted_batch = unit_manager.submit_units(c_replicas)
                    self._prof.prof('submit_md_units_end__' + c_str )

                    submitted_replicas += submitted_batch

                    unit_ids = []
                    for item in submitted_batch:
                        unit_ids.append( item.uid )    

                    self._prof.prof('wait_md_units_start__' + c_str )
                    unit_manager.wait_units( unit_ids=unit_ids)
                    self._prof.prof('wait_md_units_end__' + c_str )
                    
                #---------------------------------------------------------------
                #
                if (md_kernel.dims[dim_str[dim_int]]['type'] == 'salt'):

                    ex_prep_timing = 0.0
                    ex_sub_timing  = 0.0
                    ex_exec_timing = 0.0

                    self._prof.prof('get_all_groups_start__' + c_str)
                    all_groups = md_kernel.get_all_groups(dim_int, replicas)
                    for group in all_groups:
                        group.pop(0)
                    self._prof.prof('get_all_groups_end__' + c_str)

                    batch = []
                    r_cores = md_kernel.dims[dim_str[dim_int]]['replicas']
                    for group in all_groups:
                        if ( (len(batch)+len(group))*r_cores ) <= self.cores:
                            batch.append(group)
                        else:
                            if len(batch) == 0:
                                self.logger.info('ERROR: batch is empty, no replicas to prepare!')
                                sys.exit(1)

                            e_replicas = []
                            self._prof.prof('prepare_replica_for_exchange_start__' + c_str)
                            for group in batch:
                                for replica in group:
                                    ex_replica = md_kernel.prepare_replica_for_exchange(current_cycle, dim_int, dim_str[dim_int], group, replica, self.sd_shared_list)
                                    e_replicas.append(ex_replica)
                            self._prof.prof('prepare_replica_for_exchange_end__' + c_str)

                            self._prof.prof('submit_ex_units_start__' + c_str )
                            exchange_replicas += unit_manager.submit_units(e_replicas) 
                            self._prof.prof('submit_ex_units_end__' + c_str )
 
                            self._prof.prof('wait_ex_units_start__' + c_str )
                            unit_manager.wait_units()
                            self._prof.prof('wait_ex_units_end__' + c_str )
 
                            batch = []
                            batch.append(group)
                    if len(batch) != 0:
                        e_replicas = []
                        self._prof.prof('prepare_replica_for_exchange_start__' + c_str)
                        for group in batch:
                            for replica in group:
                                ex_replica = md_kernel.prepare_replica_for_exchange(current_cycle, dim_int, dim_str[dim_int], group, replica, self.sd_shared_list)
                                e_replicas.append(ex_replica)
                        self._prof.prof('prepare_replica_for_exchange_end__' + c_str)

                        self._prof.prof('submit_ex_units_start__' + c_str )
                        exchange_replicas += unit_manager.submit_units(e_replicas) 
                        self._prof.prof('submit_ex_units_end__' + c_str )

                        self._prof.prof('wait_ex_units_start__' + c_str )
                        unit_manager.wait_units()
                        self._prof.prof('wait_ex_units_end__' + c_str )

                    #-----------------------------------------------------------
                    # submitting unit which determines exchanges between replicas
                  
                    self._prof.prof('prepare_global_ex_calc_start__' + c_str )
                    ex_calculator = md_kernel.prepare_global_ex_calc(current_cycle, dim_int, dim_str[dim_int], replicas, self.sd_shared_list)
                    self._prof.prof('prepare_global_ex_calc_end__' + c_str )

                    self._prof.prof('submit_gl_unit_start__' + c_str )
                    global_ex_cu = unit_manager.submit_units(ex_calculator)
                    self._prof.prof('submit_gl_unit_end__' + c_str )
                    
                    self._prof.prof('wait_gl_unit_start__' + c_str )
                    unit_manager.wait_units()
                    self._prof.prof('wait_gl_unit_end__' + c_str )

                else:
                    self._prof.prof('prepare_global_ex_calc_start__' + c_str )
                    ex_calculator = md_kernel.prepare_global_ex_calc(current_cycle, dim_int, dim_str[dim_int], replicas, self.sd_shared_list)
                    self._prof.prof('prepare_global_ex_calc_end__' + c_str )

                    self._prof.prof('submit_gl_unit_start__' + c_str )
                    global_ex_cu = unit_manager.submit_units(ex_calculator)
                    self._prof.prof('submit_gl_unit_end__' + c_str )

                    self._prof.prof('wait_gl_unit_start__' + c_str )
                    unit_manager.wait_units( unit_ids=global_ex_cu.uid )
                    self._prof.prof('wait_gl_unit_end__' + c_str )

            #-------------------------------------------------------------------
            # 
            failed_cus = []              
            for r in submitted_replicas:
                if r.state != rp.DONE:
                    self.logger.info('ERROR: In D%d MD-step failed for unit:  %s' % (dim_int, r.uid))
                    failed_cus.append( r.uid )

            if len(exchange_replicas) > 0:
                for r in exchange_replicas:
                    if r.state != rp.DONE:
                        self.logger.info('ERROR: In D%d Exchange-step failed for unit:  %s' % (dim_int, r.uid))
                        failed_cus.append( r.uid )

            if global_ex_cu.state != rp.DONE:
                self.logger.info('ERROR: In D%d Global-Exchange-step failed for unit:  %s' % (dim_int, global_ex_cu.uid))
                failed_cus.append( global_ex_cu.uid )

            # do exchange of parameters  
            self._prof.prof('do_exchange_start__' + c_str )                   
            md_kernel.do_exchange(current_cycle, dim_int, dim_str[dim_int], replicas)
            # for the case when we were restarting previous simulation
            md_kernel.restart_done = True
            self._prof.prof('do_exchange_end__' + c_str ) 

            #write replica objects out
            self._prof.prof('save_replicas_start__' + c_str ) 
            md_kernel.save_replicas(current_cycle, dim_int, dim_str[dim_int], replicas)
            self._prof.prof('save_replicas_end__' + c_str )

            self.logger.info("parameters after exchange: ")
            for r in replicas:
                self.logger.info("replica: {0} type: {1} param: {2}".format(r.id, r.dims[dim_str[dim_int]]['type'], r.dims[dim_str[dim_int]]['par']) )

        #-----------------------------------------------------------------------
        # end of loop
        self._prof.prof('main_simulation_loop_end')
        self._prof.prof('run_simulation_end')

