"""
.. module:: radical.repex.execution_management_modules.exec_mng_module_pattern_a_gr
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
import radical.utils.logger as rul
from execution_management_modules.exec_mng_module import *

#-------------------------------------------------------------------------------

class ExecutionManagementModulePatternSgroup(ExecutionManagementModule):
    """This is experimental EMM for synchronous RE pattern with grouping of 
    replicas from the same group into a single CU. This EMM is designed for 
    multi-dimensional simulations. 
    Note: This module can be used only for AmberAMM.

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

        self.name = 'EmmPatternSgroup'
        self.sd_shared_list = []

#-------------------------------------------------------------------------------

    def run_simulation(self, replicas, md_kernel):
        """Runs the main loop of synchronous RE simulation with grouping option. 
        Profiling probes are inserted here.

        Args:
            replicas - list of Replica objects

            md_kernel - an instance of AMM
        """

        # ----------------------------------------------------------------------
        #
        def unit_state_change_cb(unit, state):

            if unit:            
                self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )

                if state == rp.states.FAILED:
                    self.logger.error("Log: {0:s}".format( unit.as_dict() ) )
                    # restart replica here
                    
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

        self._prof.prof('main_simulation_loop_start')
        for c in range(1,cycles*dim_count+1):

            if dim_int < dim_count:
                dim_int = dim_int + 1
            else:
                dim_int = 1
                current_cycle += 1

            self.logger.info("Performing cycle: {0}".format(current_cycle) )
            
            submitted_groups = []
            exchange_replicas = []

            c_str = '_c' + str(current_cycle) + '_d' + str(dim_int)

            # bulk_submission submision
            if bulk_submission:
                
                md_prep_timing = 0.0
                md_sub_timing  = 0.0
                md_exec_timing = 0.0

                self._prof.prof('get_all_groups_start__' + c_str)
                all_groups = md_kernel.get_all_groups(dim_int, replicas)
                for group in all_groups:
                    group.pop(0)
                self._prof.prof('get_all_groups_end__' + c_str)

                print "all_groups: "
                print all_groups

                c_units = []
                self._prof.prof('prepare_group_for_md_start__' + c_str )
                for group in all_groups:
                    compute_group = md_kernel.prepare_group_for_md(current_cycle, dim_int, dim_str[dim_int], group, self.sd_shared_list)
                    c_units.append(compute_group)
                self._prof.prof('prepare_group_for_md_end__' + c_str )

                self._prof.prof('submit_md_units_start__' + c_str )
                submitted_groups += unit_manager.submit_units(c_units)
                self._prof.prof('submit_md_units_end__' + c_str )

                self._prof.prof('wait_md_units_start__' + c_str )
                unit_manager.wait_units()
                self._prof.prof('wait_md_units_end__' + c_str )

                self._prof.prof('prepare_global_ex_calc_start__' + c_str )
                ex_calculator = md_kernel.prepare_global_ex_calc(current_cycle, dim_int, dim_str[dim_int], replicas, self.sd_shared_list)
                self._prof.prof('prepare_global_ex_calc_end__' + c_str )

                self._prof.prof('submit_gl_unit_start__' + c_str )
                global_ex_cu = unit_manager.submit_units(ex_calculator)
                self._prof.prof('submit_gl_unit_end__' + c_str )
 
                self._prof.prof('wait_gl_unit_start__' + c_str )
                unit_manager.wait_units()
                self._prof.prof('wait_gl_unit_end__' + c_str )

            #-------------------------------------------------------------------
            
            for r in submitted_groups:
                if r.state != rp.DONE:
                    self.logger.error('ERROR: In D%d MD-step failed for unit:  %s' % (dim_int, r.uid))

            if len(exchange_replicas) > 0:
                for r in exchange_replicas:
                    if r.state != rp.DONE:
                        self.logger.error('ERROR: In D%d Exchange-step failed for unit:  %s' % (dim_int, r.uid))

            if global_ex_cu.state != rp.DONE:
                self.logger.error('ERROR: In D%d Global-Exchange-step failed for unit:  %s' % (dim_int, global_ex_cu.uid))

            # do exchange of parameters    
            self._prof.prof('do_exchange_start__' + c_str )                   
            md_kernel.do_exchange(current_cycle, dim_int, dim_str[dim_int], replicas)
            # for the case when we were restarting previous simulation
            md_kernel.restart_done = True
            self._prof.prof('do_exchange_end__' + c_str )  
            
        #-----------------------------------------------------------------------
        # end of loop
        self._prof.prof('main_simulation_loop_end')
        self._prof.prof('run_simulation_end')

