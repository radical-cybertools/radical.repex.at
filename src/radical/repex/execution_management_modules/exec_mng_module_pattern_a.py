"""
.. module:: radical.repex.execution_management_modules.exec_mng_module_pattern_a
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
#
class ExecutionManagementModulePatternA(ExecutionManagementModule):
    """Execution Management Module for asynchronous RE pattern. This module 
    can be used by any AMM.

    Attributes:
        name - name of this EMM

        wait_ratio - ratio of replicas which have to finish MD simulation (before
        proceeding to exchange) to the total number of replicas. this attribute 
        is user defined

        nr_replicas - total number of replicas used for this simulation

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

        self.name        = 'EmmPatternA'
        self.wait_ratio  = float(inp_file['remd.input'].get('wait_ratio', 0.25) )
        self.nr_replicas = 0
        
        self.name = 'EmmPatternA'
        self.sd_shared_list = []

    #---------------------------------------------------------------------------
    #
    def run_simulation(self, replicas, md_kernel):
        """Runs the main loop of asynchronous RE simulation. Profiling probes 
        are inserted here.

        Args:
            replicas - list of Replica objects

            md_kernel - an instance of AMM
        """

        self.nr_replicas = md_kernel.replicas
        
        #-----------------------------------------------------------------------
        #
        def unit_state_change_cb(unit, state):
            """Callback function. It gets called every time a CU changes its 
            state.
            """
            if unit:
                self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )

                if state == rp.states.FAILED:
                    self.logger.error("Log: {0:s}".format( unit.as_dict() ) )

        #-----------------------------------------------------------------------
        
        self._prof.prof('run_simulation_start')

        CYCLES = md_kernel.nr_cycles + 1
       
        unit_manager = rp.UnitManager(self.session, scheduler=rp.SCHED_ROUND_ROBIN)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(self.pilot_object)

        dim_count = md_kernel.nr_dims
        dim_str = []
        dim_str.append('')
        for i in range(dim_count):
            s = 'd' + str(i+1)
            dim_str.append(s)

        self._prof.prof('initial_stagein_start')

        # staging shared input data in
        md_kernel.prepare_shared_data(replicas)

        shared_input_file_urls = md_kernel.shared_urls
        shared_input_files = md_kernel.shared_files

        for i in range(len(shared_input_files)):

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
        # GL = 0: submit global calculator before
        # GL = 1: submit global calculator after
        GL = 1

        #DIM = 0
        #dimensions = md_kernel.dims
        #-----------------------------------------------------------------------
        # async loop
        simulation_time = 0.0
        current_cycle = 1

        if md_kernel.restart == True:
            dim_int = md_kernel.restart_object.dimension
            c = md_kernel.restart_object.current_cycle
            for r in replicas:
                r.state = 'I'
        else:
            dim_int = 1
            c = 0

        # init required lists
        md_replicas = list()
        exchange_replicas  = list()

        completed_md_tasks = list()
        submitted_md_tasks = list()

        self.logger.info("cycle_time: {0}".format( self.cycletime) )
        c_start = datetime.datetime.utcnow()

        #-----------------------------------------------------------------------
        #
        # async algo
        #
        #-----------------------------------------------------------------------
        for r in replicas:
            r.state == 'I'

        self._prof.prof('main_simulation_loop_start')
        while (simulation_time < self.runtime*60.0 ):

            current_cycle = (c / dim_count) + 1
            if ( simulation_time < (self.runtime*60.0 - self.cycletime) ):

                # perform exchange phase
                if exchange_replicas:
                    # group replicas by dimension
                    self._prof.prof('group_ex_replicas_by_dim_start')
                    gl_exchange_dims = []
                    for r in exchange_replicas:
                        if r.cur_dim not in gl_exchange_dims:
                            gl_exchange_dims.append(r.cur_dim)
                    gl_exchange_dims = sorted(gl_exchange_dims)
                    replicas_by_dim = []
                    idx = 0
                    for d in gl_exchange_dims:
                        replicas_by_dim.append([])
                        for r in exchange_replicas:
                            if r.cur_dim == d:
                                replicas_by_dim[idx].append(r)
                        idx += 1
                    self._prof.prof('group_ex_replicas_by_dim_end')

                    #-----------------------------------------------------------
                    # do global exchange, replicas in different dimensions may 
                    # have reached this stage
                    for r_dim_list in replicas_by_dim:
                        c_str = '_c_' + str(current_cycle) + '_d_' + str(r_dim_list[0].cur_dim)
                        self._prof.prof('prepare_global_ex_calc_start__' + c_str)
                        gl_dim = r_dim_list[0].cur_dim
                        cur_cycle = r_dim_list[0].sim_cycle
                        cu_name = 'gl_ex' + c_str
                        ex_calculator = md_kernel.prepare_global_ex_calc(c, gl_dim, dim_str[gl_dim], r_dim_list , self.sd_shared_list)   
                        self._prof.prof('prepare_global_ex_calc_end__' + c_str)
                        ex_calculator.name = cu_name
                        self._prof.prof('submit_gl_unit_start__' + c_str)
                        global_ex_cu = unit_manager.submit_units(ex_calculator)
                        self._prof.prof('submit_gl_unit_end__' + c_str)

                        # wait for exchange to finish
                        self._prof.prof('wait_gl_unit_start__' + c_str)
                        unit_manager.wait_units( unit_ids=global_ex_cu.uid )
                        self._prof.prof('wait_gl_unit_end__' + c_str)
                        sleep = 0
                        gl_state = 'None'
                        while (gl_state != 'Done'):
                            gl_state = global_ex_cu.state
                            time.sleep(1)
                            sleep += 1
                            if ( sleep > 60 ):
                                gl_state = 'Done'
                        #-------------------------------------------------------
                        # update dimension count and set state to 'I'
                        for r in r_dim_list:
                            r.state = 'I'
                            if r.cur_dim < dim_count:
                                r.cur_dim += 1
                            else:
                                r.cur_dim = 1
                        #-------------------------------------------------------
                        # exchange params
                        self._prof.prof('do_exchange_start__' + c_str)
                        md_kernel.do_exchange(c, gl_dim, dim_str[gl_dim], r_dim_list)
                        self._prof.prof('do_exchange_end__' + c_str)
                        #write replica objects out
                        self._prof.prof('save_replicas_start__' + c_str)
                        md_kernel.save_replicas(c, gl_dim, dim_str[gl_dim], replicas)
                        self._prof.prof('save_replicas_end__' + c_str)

                    #-----------------------------------------------------------
                    # submit for MD replicas which finished exchange
                    md_replicas = list()
                    for r in replicas:
                        if r.state == 'I':
                            md_replicas.append(r)

                    c_replicas = []
                    self._prof.prof('prepare_replica_for_md_start')
                    for replica in md_replicas:
                        r_dim = replica.cur_dim
                        group = md_kernel.get_replica_group(r_dim, replicas, replica)
                        cu_name = 'id_' + str(replica.id) + '_gr_' + str(replica.group_idx[r_dim-1]) + '_c_' + str(current_cycle) + '_d_' + str(r_dim)
                        cu_tuple = cu_name.split('_')
                        compute_replica = md_kernel.prepare_replica_for_md(current_cycle, r_dim, dim_str[r_dim], group, replica, self.sd_shared_list)
                        compute_replica.name = cu_name
                        c_replicas.append( compute_replica )
                    self._prof.prof('prepare_replica_for_md_end')
                    self._prof.prof('submit_md_units_start')
                    sub_replicas = unit_manager.submit_units(c_replicas)
                    self._prof.prof('submit_md_units_end')
                    submitted_md_tasks += sub_replicas

                    for r in md_replicas:
                        r.state = 'MD'

                #---------------------------------------------------------------
                # perform MD phase
                md_replicas = list()
                for r in replicas:
                    if r.state == 'I':
                        md_replicas.append(r)

                if md_replicas:
                    c_replicas = []
                    self._prof.prof('prepare_replica_for_md_start')
                    for replica in md_replicas:
                        r_dim = replica.cur_dim
                        group = md_kernel.get_replica_group(r_dim, replicas, replica)
                        cu_name = 'id_' + str(replica.id) + '_gr_' + str(replica.group_idx[r_dim-1]) + '_c_' + str(current_cycle) + '_d_' + str(r_dim)
                        cu_tuple = cu_name.split('_')
                        compute_replica = md_kernel.prepare_replica_for_md(current_cycle, r_dim, dim_str[r_dim], group, replica, self.sd_shared_list)
                        compute_replica.name = cu_name
                        c_replicas.append( compute_replica )
                    self._prof.prof('prepare_replica_for_md_end')
                    self._prof.prof('submit_md_units_start')
                    sub_replicas = unit_manager.submit_units(c_replicas)
                    self._prof.prof('submit_md_units_end')
                    submitted_md_tasks += sub_replicas
                    for r in md_replicas:
                        r.state = 'MD'
                    # for the case when we were restarting previous simulation
                    md_kernel.restart_done = True

                #---------------------------------------------------------------
                # wait loop
                self._prof.prof('wait_md_start')
                wait_size = int(self.nr_replicas * self.wait_ratio)
                if wait_size == 0:
                    wait_size = 2
                wait_time = 0
                count_of_completed = 0
                #---------------------------------------------------------------
                # start of while loop (waiting for MD tasks to finish)
                while (count_of_completed <= wait_size):
                    # update completed_md_tasks
                    for cu in submitted_md_tasks:
                        if cu.state == 'Done':
                            if cu not in completed_md_tasks:
                                completed_md_tasks.append(cu)

                    # enter this loop only of there are enough CUs
                    if (len(completed_md_tasks) > wait_size):
                        all_gr_list = list()
                        for idx, cunit in enumerate(completed_md_tasks):
                            cu = completed_md_tasks[idx]
                            r_tuple_1 = cu.name.split('_')
                            # check if replicas from same group are finished
                            add = 0
                            add_to_sublist = None
                            for sublist in all_gr_list:
                                for item in sublist:
                                    r_tuple_2 = item.split('_')
                                    # if in same group and in same dimension
                                    if r_tuple_1[3] == r_tuple_2[3] and r_tuple_1[7] == r_tuple_2[7]:
                                        add_to_sublist = sublist
                                        add = 1
                            # in all_gr_list already are replicas from the same 
                            # group and dimension as current cu, so we add to 
                            # existing gr_list
                            if add == 1:
                                index = all_gr_list.index(add_to_sublist)
                                all_gr_list[index].append(cu.name)
                            # in all_gr_list there are no replicas from the same 
                            # group and dimension as current cu, so we add new 
                            # gr_list
                            if add == 0:     
                                gr_list = list()
                                gr_list.append(cu.name)
                                all_gr_list.append(gr_list)

                        # updating count_of_completed
                        count_of_completed = 0
                        cus_to_exchange_names = list()
                        for item in all_gr_list:
                            # we only count groups with 2 or more replicas 
                            # because each replica must have a partner
                            group_size = len(item)
                            if group_size > 1:
                                # in each group must be even number of replicas
                                if ((group_size % 2) != 0):
                                    item.pop()
                                cus_to_exchange_names += item
                        for item in cus_to_exchange_names:
                            count_of_completed += 1
                        if count_of_completed < wait_size:
                            time.sleep(1)
                            wait_time += 1
                    else:
                        time.sleep(1)
                        wait_time += 1

                self._prof.prof('wait_md_end')
                # end of while loop   
                #---------------------------------------------------------------
                # updating submitted_md_tasks: we remove all cus which are in
                # completed_md_tasks, regardless if they proceed to exchange 
                # or not
                self._prof.prof('updating submitted_md_tasks_start')
                idx_list = list()
                for i,cu1 in enumerate(completed_md_tasks): 
                    for j,cu2 in enumerate(submitted_md_tasks):
                        if cu1.name == cu2.name:
                            idx_list.append(j)
                # must sort to maintain the order
                idx_list.sort(reverse=True)
                for i,j in enumerate(idx_list):
                    submitted_md_tasks.pop(j)
                self._prof.prof('updating submitted_md_tasks_end')

                self._prof.prof('populating_cus_to_exchange_start')
                # populating cus_to_exchange
                cus_to_exchange = list()
                for item in cus_to_exchange_names:
                    for idx, cunit in enumerate(completed_md_tasks):
                        cu = completed_md_tasks[idx]
                        if item == cu.name:
                            cus_to_exchange.append(cu)
                self._prof.prof('populating_cus_to_exchange_end')

                # updating completed_md_tasks: removing tasks which proceed to
                # exchange
                self._prof.prof('updating_completed_md_tasks_start')
                idx_list = list()
                for i,cu1 in enumerate(cus_to_exchange): 
                    for j,cu2 in enumerate(completed_md_tasks):
                        if cu1.name == cu2.name:
                            idx_list.append(j)
                # must sort to maintain the order
                idx_list.sort(reverse=True)
                for i,j in enumerate(idx_list):
                    completed_md_tasks.pop(j)
                self._prof.prof('updating_completed_md_tasks_end')

                # update simulation time
                c_end = datetime.datetime.utcnow()
                simulation_time = (c_end - c_start).total_seconds()
                c += 1

                self._prof.prof('populating_exchange_replicas_start')
                # populating exchange_replicas
                exchange_replicas = list()
                for cu in cus_to_exchange:
                    if cu.state == 'Done':
                        for r in replicas:
                            cu_name = cu.name.split('_')
                            if str(r.id) == cu_name[1]:
                                exchange_replicas.append(r)
                                r.state = 'EX'
                self._prof.prof('populating_exchange_replicas_end')
                
        #-----------------------------------------------------------------------
        # end of loop

        self._prof.prof('main_simulation_loop_end')
        self._prof.prof('run_simulation_end')

