"""
.. module:: radical.repex.execution_management_modules.exec_mng_module_pattern_a
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
import radical.pilot as rp
import radical.utils.logger as rul
from execution_management_modules.exec_mng_module import *

#-------------------------------------------------------------------------------
#
class ExecutionManagementModulePatternA(ExecutionManagementModule):
    
    def __init__(self, inp_file, rconfig):

        ExecutionManagementModule.__init__(self, inp_file, rconfig)

        self.name             = 'EMM-pattern-A'
        self.logger           = rul.get_logger ('radical.repex', self.name)
        self.wait_ratio       = float(inp_file['remd.input'].get('wait_ratio', 0.125) )
        self.running_replicas = int(inp_file['remd.input'].get('running_replicas', 0) )
        if self.running_replicas == 0:
            self.running_replicas = self.cores - int(KERNELS[self.resource]["params"].get("cores") )
        
        self.sd_shared_list = []

    #---------------------------------------------------------------------------
    #
    def run_simulation(self, replicas, md_kernel):
        
        if self.running_replicas > len(replicas):
            self.running_replicas = len(replicas)

        # ----------------------------------------------------------------------
        #
        def unit_state_change_cb(unit, state):
            """This is a callback function. It gets called very time a 
            ComputeUnit changes its state.
            """
            if unit:
                self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )

                if state == rp.states.FAILED:
                    self.logger.error("Log: {0:s}".format( unit.as_dict() ) )

        #-----------------------------------------------------------------------
        #
        CYCLES = md_kernel.nr_cycles + 1

        do_profile = os.getenv('REPEX_PROFILING', '0')
       
        unit_manager = rp.UnitManager(self.session, scheduler=rp.SCHED_ROUND_ROBIN)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(self.pilot_object)

        dim_count = md_kernel.nr_dims
        dim_str = []
        dim_str.append('')
        for i in range(dim_count):
            s = 'd' + str(i+1)
            dim_str.append(s)

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

        while (simulation_time < self.runtime*60.0 ):

            current_cycle = (c / dim_count) + 1
            if ( simulation_time < (self.runtime*60.0 - self.cycletime) ):

                #---------------------------------------------------------------
                # perform exchange phase
                if exchange_replicas:
                    # group replicas by dimension
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

                    #-----------------------------------------------------------
                    # do global exchange, replicas in different dimensions may 
                    # have reached this stage
                    for r_dim_list in replicas_by_dim:
                        gl_dim = r_dim_list[0].cur_dim
                        cur_cycle = r_dim_list[0].sim_cycle
                        cu_name = 'gl_ex' + '_c_' + str(current_cycle) + '_d_' + str(r_dim_list[0].cur_dim)
                        ex_calculator = md_kernel.prepare_global_ex_calc(c, gl_dim, dim_str[gl_dim], r_dim_list , self.sd_shared_list)   
                        ex_calculator.name = cu_name
                        global_ex_cu = unit_manager.submit_units(ex_calculator)

                        # wait for exchange to finish
                        unit_manager.wait_units( unit_ids=global_ex_cu.uid )
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
                        md_kernel.do_exchange(c, gl_dim, dim_str[gl_dim], r_dim_list)
                        #write replica objects out
                        md_kernel.save_replicas(c, gl_dim, dim_str[gl_dim], replicas)
                        

                    #-----------------------------------------------------------
                    # submit for MD replicas which finished exchange
                    md_replicas = list()
                    for r in replicas:
                        if r.state == 'I':
                            md_replicas.append(r)

                    c_replicas = []
                    for replica in md_replicas:
                        r_dim = replica.cur_dim
                        group = md_kernel.get_replica_group(r_dim, replicas, replica)
                        cu_name = 'id_' + str(replica.id) + '_gr_' + str(replica.group_idx[r_dim-1]) + '_c_' + str(current_cycle) + '_d_' + str(r_dim)
                        cu_tuple = cu_name.split('_')
                        compute_replica = md_kernel.prepare_replica_for_md(current_cycle, r_dim, dim_str[r_dim], group, replica, self.sd_shared_list)
                        compute_replica.name = cu_name
                        c_replicas.append( compute_replica )
                    sub_replicas = unit_manager.submit_units(c_replicas)
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
                    for replica in md_replicas:
                        r_dim = replica.cur_dim
                        group = md_kernel.get_replica_group(r_dim, replicas, replica)
                        cu_name = 'id_' + str(replica.id) + '_gr_' + str(replica.group_idx[r_dim-1]) + '_c_' + str(current_cycle) + '_d_' + str(r_dim)
                        cu_tuple = cu_name.split('_')
                        compute_replica = md_kernel.prepare_replica_for_md(current_cycle, r_dim, dim_str[r_dim], group, replica, self.sd_shared_list)
                        compute_replica.name = cu_name
                        c_replicas.append( compute_replica )
                    sub_replicas = unit_manager.submit_units(c_replicas)
                    submitted_md_tasks += sub_replicas
                    for r in md_replicas:
                        r.state = 'MD'

                #---------------------------------------------------------------
                # wait loop
                wait_size = int(self.running_replicas * self.wait_ratio)
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
                # end of while loop   
                #---------------------------------------------------------------
                # updating submitted_md_tasks: we remove all cus which are in
                # completed_md_tasks, regardless if they proceed to exchange 
                # or not
                idx_list = list()
                for i,cu1 in enumerate(completed_md_tasks): 
                    for j,cu2 in enumerate(submitted_md_tasks):
                        if cu1.name == cu2.name:
                            idx_list.append(j)
                # must sort to maintain the order
                idx_list.sort(reverse=True)
                for i,j in enumerate(idx_list):
                    submitted_md_tasks.pop(j)

                # populating cus_to_exchange
                cus_to_exchange = list()
                for item in cus_to_exchange_names:
                    for idx, cunit in enumerate(completed_md_tasks):
                        cu = completed_md_tasks[idx]
                        if item == cu.name:
                            cus_to_exchange.append(cu)

                # updating completed_md_tasks: removing tasks which proceed to
                # exchange
                idx_list = list()
                for i,cu1 in enumerate(cus_to_exchange): 
                    for j,cu2 in enumerate(completed_md_tasks):
                        if cu1.name == cu2.name:
                            idx_list.append(j)
                # must sort to maintain the order
                idx_list.sort(reverse=True)
                for i,j in enumerate(idx_list):
                    completed_md_tasks.pop(j)

                # update simulation time
                c_end = datetime.datetime.utcnow()
                simulation_time = (c_end - c_start).total_seconds()
                c += 1

                # populating exchange_replicas
                exchange_replicas = list()
                for cu in cus_to_exchange:
                    if cu.state == 'Done':
                        for r in replicas:
                            cu_name = cu.name.split('_')
                            if str(r.id) == cu_name[1]:
                                exchange_replicas.append(r)
                                r.state = 'EX'
        #-----------------------------------------------------------------------
        # end of loop

