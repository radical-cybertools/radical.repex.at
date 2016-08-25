"""
.. module:: radical.repex.pilot_kernels.pilot_kernel_pattern_a
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
from pilot_kernels.pilot_kernel import *

#-------------------------------------------------------------------------------
#
class PilotKernelPatternAmultiD(PilotKernel):
    
    def __init__(self, inp_file, rconfig):

        PilotKernel.__init__(self, inp_file, rconfig)

        self.name             = 'exec-pattern-A'
        self.logger           = rul.get_logger ('radical.repex', self.name)
        self.wait_ratio       = float(inp_file['remd.input'].get('wait_ratio', 0.125) )
        self.running_replicas = int(inp_file['remd.input'].get('running_replicas', 0) )
        if self.running_replicas == 0:
            self.running_replicas = self.cores - int(KERNELS[self.resource]["params"].get("cores") )
        
        self.sd_shared_list = []

    #---------------------------------------------------------------------------
    #
    def update_group_idx(self, cu_tuple, running_replicas):
        
        """
        for r in running_replicas:
            if cu_tuple[1] == str(r.id):
                r_dim = int(cu_tuple[7])
                group_nr = r.group_idx[r_dim-1]
        cu_name = 'id_' + cu_tuple[1] + '_gr_' + str(group_nr) + '_c_' + cu_tuple[5] + '_d_' + cu_tuple[7]
        """
        #return cu_name.split('_')
        return cu_tuple

    #---------------------------------------------------------------------------
    #
    def run_simulation(self, replicas, md_kernel ):
        
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

        self._prof = rp.utils.Profiler(self.name)
        self._prof.prof('start_run')
        self._prof.prof('stagein_start')

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
        
        self._prof.prof('stagein_end')

        #-----------------------------------------------------------------------
        # GL = 0: submit global calculator before
        # GL = 1: submit global calculator after
        GL = 1

        #DIM = 0
        #dimensions = md_kernel.dims
        #-----------------------------------------------------------------------
        # async loop
        simulation_time = 0.0
        running_replicas = []
        sub_md_replicas = []
        sub_ex_replicas = []
        
        current_cycle = 1

        if md_kernel.restart == True:
            dim_int = md_kernel.restart_object.dimension
            c = md_kernel.restart_object.current_cycle
            for r in replicas:
                r.state = 'I'
        else:
            dim_int = 1
            c = 0

        replicas_for_exchange = []
        replicas_for_md = []
        completed_cus = []

        self.logger.info("cycle_time: {0}".format( self.cycletime) )
        c_start = datetime.datetime.utcnow()

        #-----------------------------------------------------------------------
        
        self._prof.prof('sim_loop_start')
        while (simulation_time < self.runtime*60.0 ):

            current_cycle = (c / dim_count) + 1
            if ( simulation_time < (self.runtime*60.0 - self.cycletime) ):
                replicas_for_md = []
                for r in replicas:
                    if r.state == 'I':
                        r.state = 'W'
                    if r.state == 'W':
                        replicas_for_md.append(r)

                if (len(replicas_for_md) != 0):
                    c_str = '_c_' + str(current_cycle) + '_d_' + str(replicas_for_md[0].cur_dim)
                    self._prof.prof('md_prep_start_1' + c_str )
                    c_replicas = []
                    for replica in replicas_for_md:
                        r_dim = replica.cur_dim
                        group = md_kernel.get_replica_group(r_dim, replicas, replica)
                        cu_name = 'id_' + str(replica.id) + '_gr_' + str(replica.group_idx[r_dim-1]) + '_c_' + str(current_cycle) + '_d_' + str(r_dim)
                        cu_tuple = cu_name.split('_')
                        self.logger.info( "FIRST LOOP: Preparing replica id {0} for MD in dim {1}".format(cu_tuple[1], cu_tuple[7]) )
                        compute_replica = md_kernel.prepare_replica_for_md(current_cycle, r_dim, dim_str[r_dim], group, replica, self.sd_shared_list)
                        compute_replica.name = cu_name
                        c_replicas.append( compute_replica )
                    self._prof.prof('md_prep_end_1' + c_str )
                        
                    self._prof.prof('md_sub_start_1' + c_str )
                    sub_replicas = unit_manager.submit_units(c_replicas)
                    self._prof.prof('md_sub_end_1' + c_str )
                    sub_md_replicas += sub_replicas

                    for r in replicas_for_md:
                        r.state = 'R'
                    running_replicas += replicas_for_md

                self.logger.info( "sub_md_replicas: {0}".format( len(sub_md_replicas) ) )

                if (len(replicas_for_exchange) != 0):
                    gl_exchange_dims = []
                    for r in replicas_for_exchange:
                        if r.cur_dim not in gl_exchange_dims:
                            gl_exchange_dims.append(r.cur_dim)
                    self.logger.info( "gl_exchange_dims: {0}".format(gl_exchange_dims) )

                    gl_exchange_dims = sorted(gl_exchange_dims)
                    replicas_by_dim = []
                    idx = 0
                    for d in gl_exchange_dims:
                        replicas_by_dim.append([])
                        for r in replicas_for_exchange:
                            if r.cur_dim == d:
                                replicas_by_dim[idx].append(r)
                        idx += 1

                    #for d in replicas_by_dim:
                    #    for r in d:
                    #        self.logger.info( "replica_id: {0} cur_dim: {1}".format(r.id, r.cur_dim) )

                    #-----------------------------------------------------------
                    # do global exchange, replicas in different dimensions may 
                    # have reached this stage
                    for replicas_d_list in replicas_by_dim:
                        gl_dim = replicas_d_list[0].cur_dim
                        cur_cycle = replicas_d_list[0].sim_cycle
                        cu_name = 'gl_ex_cu' + c_str
                        self._prof.prof('gl_ex_prep_start_1' + c_str )
                        ex_calculator = md_kernel.prepare_global_ex_calc(c, gl_dim, dim_str[gl_dim], replicas_d_list , self.sd_shared_list)   
                        ex_calculator.name = cu_name
                        self.logger.info( "FIRST LOOP: Preparing global calc in dim {0} cycle {1}".format(gl_dim, cur_cycle) )
                        self._prof.prof('gl_ex_prep_end_1' + c_str )
                        self._prof.prof('gl_ex_sub_start_1' + c_str )
                        global_ex_cu = unit_manager.submit_units(ex_calculator)
                        self._prof.prof('gl_ex_sub_end_1' + c_str )

                        self._prof.prof('gl_ex_wait_start_1' + c_str )
                        unit_manager.wait_units( unit_ids=global_ex_cu.uid )
                        self._prof.prof('gl_ex_wait_end_1' + c_str )

                        gl_state = 'None'
                        sleep = 0
                        while (gl_state != 'Done'):
                            self.logger.info( "Waiting for global calc to finish!" )
                            gl_state = global_ex_cu.state
                            time.sleep(1)
                            sleep += 1
                            if ( sleep > 60 ):
                                self.logger.info( "Warning: global calc never reached Done state..." )
                                gl_state = 'Done'

                        self.logger.info( "Global calc {0} finished!".format( global_ex_cu.uid ) )
                        self._prof.prof('local_proc_start_1' + c_str )
                        # exchange is a part of MD CU
                        for r in replicas_d_list:
                            self.logger.info( "replica id {0} state changed to E".format( r.id ) )
                            r.state = 'E'
                            if r.cur_dim < dim_count:
                                r.cur_dim += 1
                            else:
                                r.cur_dim = 1
                        
                        if global_ex_cu.state == 'Done':
                            self.logger.info( "Got exchange pairs!" )
                            #md_kernel.do_exchange(c, gl_dim, dim_str[gl_dim], replicas_d_list)

                            #write replica objects out
                            md_kernel.save_replicas(c, gl_dim, dim_str[gl_dim], replicas)
                            
                            for r in replicas_d_list:
                                self.logger.info( "replica id {0} dim {1} state changed to W".format( r.id, r.cur_dim ) )
                                r.state = 'W'

                    #-----------------------------------------------------------
                    # updating group indexes after exchange
                    for d in range(1,dim_count+1):
                        md_kernel.assign_group_idx(replicas, d)

                    #-----------------------------------------------------------
                    # submit for MD within same cycle
                    replicas_for_md = []
                    for r in replicas:
                        if r.state == 'W':
                            replicas_for_md.append(r)

                    c_str = '_c_' + str(current_cycle) + '_d_' + str(replicas_for_md[0].cur_dim)
                    self._prof.prof('local_proc_end_1' + c_str )
                    if (len(replicas_for_md) != 0):
                        self._prof.prof('md_prep_start_2' + c_str )
                        c_replicas = []
                        for replica in replicas_for_md:
                            r_dim = replica.cur_dim
                            group = md_kernel.get_replica_group(r_dim, replicas, replica)
                            cu_name = 'id_' + str(replica.id) + '_gr_' + str(replica.group_idx[r_dim-1]) + '_c_' + str(current_cycle) + '_d_' + str(r_dim)
                            cu_tuple = cu_name.split('_')
                            self.logger.info( "SECOND LOOP: Preparing replica id {0} for MD in dim {0}".format(cu_tuple[1], cu_tuple[7]) )
                            compute_replica = md_kernel.prepare_replica_for_md(current_cycle, r_dim, dim_str[r_dim], group, replica, self.sd_shared_list)
                            compute_replica.name = cu_name
                            c_replicas.append( compute_replica )
                        self._prof.prof('md_prep_end_2' + c_str )
                            
                        self._prof.prof('md_sub_start_2' + c_str )
                        sub_replicas = unit_manager.submit_units(c_replicas)
                        self._prof.prof('md_sub_end_2' + c_str )
                        sub_md_replicas += sub_replicas

                        for r in replicas_for_md:
                            r.state = 'R'
                        running_replicas += replicas_for_md

                #---------------------------------------------------------------
                completed = 0
                self._prof.prof('local_wait_start_1' + c_str )
                
                #---------------------------------------------------------------
                # wait loop

                self.logger.info( "second wait....." )
                wait_size = int(self.running_replicas * self.wait_ratio)
                if wait_size == 0:
                    wait_size = 1
                self.logger.info( "wait size: {0}".format( wait_size ) )

                wait_time_2 = 0
                
                total_completed_count = 0
                while (total_completed_count < wait_size):
                    for cu in sub_md_replicas:
                        if cu.state == 'Done':
                            if cu not in completed_cus:
                                completed_cus.append(cu)

                    if (len(completed_cus) > wait_size):
                        processed_cus = []
                        all_gr_list = []
                        for cu in completed_cus:
                            r_tuple = self.update_group_idx(cu.name.split('_'), replicas)
                            # check if replicas from same group are finished after 1st wait
                            add = 0
                            add_to_sublist = None
                            for sublist in all_gr_list:
                                for item in sublist:
                                    r_tuple_add = self.update_group_idx(item.split('_'), replicas)
                                    # if in same group and in same dimension
                                    if r_tuple[3] == r_tuple_add[3] and r_tuple[7] == r_tuple_add[7]:
                                        add_to_sublist = sublist
                                        add = 1
                            if add == 1:
                                index = all_gr_list.index(add_to_sublist)
                                all_gr_list[index].append(cu.name)
                                processed_cus.append(cu.name)
                            if add == 0:     
                                gr_list = []
                                gr_list.append(cu.name)
                                all_gr_list.append(gr_list)
                                processed_cus.append(cu.name)

                        self.logger.info( "all_gr_list in while: {0}".format( all_gr_list )  )
                        all_gr_list_sizes = []
                        for gr_list in all_gr_list:
                            all_gr_list_sizes.append( len(gr_list) )
                        self.logger.info( "all_gr_list_sizes in while: {0}".format( all_gr_list_sizes ) )
                    
                        #-------------------------------------------------------
                        # updating total_completed_count
                        total_completed_count = 0
                        tmp_all_gr_list = list()
                        #total_completed_count = 0
                        for item in all_gr_list:
                            # we only count groups with 2 or more replicas 
                            if len(item) > 1:
                                tmp_all_gr_list.append(item)
                        for item in tmp_all_gr_list:
                            for i in item:
                                total_completed_count += 1

                        if total_completed_count < wait_size:
                            time.sleep(2)
                            wait_time_2 += 2
                    else:
                        time.sleep(2)
                        wait_time_2 += 2

                #---------------------------------------------------------------
                # end of while loop   
                self.logger.info( "wait time: {0}".format( wait_time_2 ) )

                cus_to_exchange = list(completed_cus)

                all_gr_list = list(tmp_all_gr_list)
                #---------------------------------------------------------------
                # updating cus_to_exchange
                cus_to_exchange_new = list()
                for cu in completed_cus:
                    c_tuple = self.update_group_idx(cu.name.split('_'), replicas)
                    for item in all_gr_list:
                        for nu in item:
                            n_tuple = nu.split('_')
                            if c_tuple[3] == n_tuple[3] and c_tuple[7] == n_tuple[7] and c_tuple[1] == n_tuple[1]:
                                cus_to_exchange_new.append(cu) 
                cus_to_exchange = list(cus_to_exchange_new)

                cus_to_exchange_names = list()
                for cu in cus_to_exchange_new:
                    cus_to_exchange_names.append(cu.name)
                #self.logger.info( "all_gr_list middle: {0}".format( all_gr_list )  )
                #self.logger.info( "cus_to_exchange_names:    {0}".format( cus_to_exchange_names )  )
                #self.logger.info( "size cus_to_exchange: {0} size all_gr_list: {1}".format( len(cus_to_exchange), total_completed_count ) )

                #---------------------------------------------------------------
                # in each group must be only even number of replicas
                dims = []
                cus_to_exchange_new = []
                for cu in cus_to_exchange:
                    cu_tuple = cu.name.split('_')
                    if cu_tuple[7] not in dims:
                        dims.append(cu_tuple[7])
                self.logger.info( "dims: {0}".format( dims )  )
                
                for dim in dims:
                    cus_to_exchange_gr = []
                    cus_to_exchange_gr_names = []

                    gr_ids = []
                    max_id = 0
                    for cu in cus_to_exchange:
                        cu_tuple = self.update_group_idx(cu.name.split('_'), replicas)
                        if (cu_tuple[7] == dim):
                            if max_id < int(cu_tuple[3]):
                                max_id = int(cu_tuple[3])
                    self.logger.info( "dim: {0} max_id: {1}".format(dim, max_id )  )

                    for i in range(max_id+1):
                         cus_to_exchange_gr.append([None])
                         cus_to_exchange_gr_names.append([None])

                    for cu in cus_to_exchange:
                        cu_tuple = self.update_group_idx(cu.name.split('_'), replicas)
                        if cu_tuple[7] == dim:
                            #self.logger.info( "dim: {0} cur_id: {1}".format(dim, int(cu_tuple[3]) )  )
                            cus_to_exchange_gr[int(cu_tuple[3])].append(cu)
                            cus_to_exchange_gr_names[int(cu_tuple[3])].append(cu.name)

                    for item in cus_to_exchange_gr:
                        item.pop(0)
                        if len(item) % 2 != 0:
                            item.pop(0)
                        cus_to_exchange_new += item

                    self.logger.info( "dim: {0} BEFORE UPDATE cus_to_exchange_gr_names: {1}".format(dim, cus_to_exchange_gr_names ) )
                    for item in cus_to_exchange_gr_names:
                        item.pop(0)
                        if len(item) % 2 != 0:
                            item.pop(0)
                    # removing empty lists
                    try:
                        for i in range(len(cus_to_exchange_gr_names)):
                            if (len(cus_to_exchange_gr_names[i]) == 0):
                                cus_to_exchange_gr_names.pop(i)
                    except:
                        pass
                    self.logger.info( "dim: {0} AFTER UPDATE cus_to_exchange_gr_names: {1}".format(dim, cus_to_exchange_gr_names ) )

                cus_to_exchange = cus_to_exchange_new
                #self.logger.info( "dim: {0} UPDATED cus_to_exchange: {1}".format(dim, cus_to_exchange ) )

                # updating completed_cus
                completed_cus_new = list(completed_cus)
                for cu1 in cus_to_exchange:
                    for cu2 in completed_cus:
                        if cu1.name == cu2.name:
                            completed_cus_new.remove(cu2)
                completed_cus = list(completed_cus_new)

                #---------------------------------------------------------------
                
                self._prof.prof('local_wait_end_1' + c_str )
                self._prof.prof('local_proc_start_2' + c_str )

                c_end = datetime.datetime.utcnow()
                simulation_time = (c_end - c_start).total_seconds()
                self.logger.info( "Simulation time: {0}".format( simulation_time ) )

                c += 1

                self.logger.info( "Incremented current cycle: {0}".format( current_cycle ) )
                replicas_for_exchange = []
                rm_cus = []
                for cu in cus_to_exchange:
                    if cu.state == 'Done':
                        for r in running_replicas:
                            cu_name = cu.name.split('_')
                            if str(r.id) == cu_name[1]:
                                self.logger.info( "Replica {0} finished MD for dim {1}".format( r.id, r.cur_dim ) )
                                replicas_for_exchange.append(r)
                                running_replicas.remove(r)
                                rm_cus.append(cu)
                                r.state = 'M'
                for cu in rm_cus:
                    sub_md_replicas.remove(cu)
                self._prof.prof('local_proc_end_2' + c_str )

        #-----------------------------------------------------------------------
        # end of loop
        self._prof.prof('sim_loop_end')
