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
import radical.pilot
import radical.utils.logger as rul
from pilot_kernels.pilot_kernel import *

#-------------------------------------------------------------------------------
#
class PilotKernelPatternAmultiD(PilotKernel):
    
    def __init__(self, inp_file, rconfig):
        """Constructor.

        Arguments:
        inp_file - json input file with Pilot and NAMD related parameters as 
        specified by user 
        """

        PilotKernel.__init__(self, inp_file, rconfig)

        self.name = 'exec-pattern-A'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        self.sd_shared_list = []

    #---------------------------------------------------------------------------
    #
    def run_simulation(self, replicas, md_kernel ):
        """This function runs the main loop of RE simulation for RE scheme 2a.

        Arguments:
        replicas - list of Replica objects
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

        #-----------------------------------------------------------------------
        #
        CYCLES = md_kernel.nr_cycles + 1

        do_profile = os.getenv('REPEX_PROFILING', '0')
       
        unit_manager = radical.pilot.UnitManager(self.session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(self.pilot_object)

        stagein_start = datetime.datetime.utcnow()

        # creating restraint files for US case 
        if md_kernel.name == 'ak-patternB-us':
            for r in replicas:
                md_kernel.build_restraint_file(r)

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

        # make sure data is staged
        time.sleep(3)
        
        stagein_end = datetime.datetime.utcnow()

        # absolute simulation start time
        start = datetime.datetime.utcnow()

        hl_performance_data = {}
        cu_performance_data = {}

        #------------------------
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
        sub_global_ex = []
        sub_global_cycles = []
        sub_global_repl = []
        current_cycle = 0
        c = 0

        dim_int = 0
        dim_count = md_kernel.nr_dims
        dim_str = []
        dim_str.append('')
        for i in range(dim_count):
            s = 'd' + str(i+1)
            dim_str.append(s)

        replicas_for_exchange = []
        replicas_for_md = []

        self.logger.info("cycle_time: {0}".format( self.cycletime) )
        c_start = datetime.datetime.utcnow()

        while (simulation_time < self.runtime*60.0 ):

            if dim_int < dim_count:
                dim_int = dim_int + 1
            else:
                dim_int = 1
            
            if (simulation_time < (self.runtime*60.0 - self.cycletime) ):
                replicas_for_md = []
                for r in replicas:
                    if r.state == 'I':
                        r.state = 'W'
                    if r.state == 'W':
                        replicas_for_md.append(r)

                if (len(replicas_for_md) != 0):
                    c_replicas = []
                    for replica in replicas_for_md:
                        cu_name = str(replica.id) + '_' + str(replica.group_idx[dim_int-1])
                        self.logger.info( "cu_name: {0}".format(cu_name) )
                        compute_replica = md_kernel.prepare_replica_for_md(dim_int, dim_str[dim_int], replicas_for_md, replica, self.sd_shared_list)
                        compute_replica.name = cu_name
                        c_replicas.append( compute_replica )
                        
                    sub_replicas = unit_manager.submit_units(c_replicas)
                    sub_md_replicas += sub_replicas

                    for r in replicas_for_md:
                        r.state = 'R'
                    running_replicas += replicas_for_md

                print "sub_md_replicas: {0}".format( len(sub_md_replicas) )

                if (len(replicas_for_exchange) != 0):
                    sub_global_repl.append( replicas_for_exchange ) 

                    # current cycle???? how it is determined
                    ex_calculator = md_kernel.prepare_global_ex_calc(current_cycle, dim_int, dim_str[dim_int], replicas_for_exchange, self.sd_shared_list)   
                    global_ex_cu = unit_manager.submit_units(ex_calculator)
                    sub_global_ex.append( global_ex_cu )
                    sub_global_cycles.append( current_cycle )

                    #for r in replicas_for_exchange:
                    #    r.state = 'R'
                    #running_replicas += replicas_for_exchange

                    # added below
                    #-----------------------------------------------------------

                    unit_manager.wait_units( unit_ids=global_ex_cu.uid )
                    gl_state = 'None'
                    while (gl_state != 'Done'):
                        self.logger.info( "Waiting for global calc to finish!" )
                        gl_state = global_ex_cu.state
                        c_end = datetime.datetime.utcnow()
                        simulation_time = (c_end - c_start).total_seconds()
                        time.sleep(1)
                        if ( simulation_time > self.runtime*60.0 ):
                            gl_state = 'Done'

                    self.logger.info( "Global calc {0} finished!".format( global_ex_cu.uid ) )

                    # exchange is a part of MD CU
                    for r in replicas_for_exchange:
                        r.state = 'E'

                    #for cu in rm_cus:
                    #    sub_ex_replicas.remove(cu)
                    
                    if (len(sub_global_ex) != 0):
                        if sub_global_ex[0].state == 'Done':

                            #print "got exchange pairs!"
                            self.logger.info( "Got exchange pairs!" )

                            sub_global_ex.pop(0)

                            ex_repl = sub_global_repl[0]
                            sub_global_repl.pop(0)

                            cycle = sub_global_cycles[0]
                            sub_global_cycles.pop(0)
         
                            md_kernel.do_exchange(cycle, dim_int, dim_str[dim_int], ex_repl)

                            for r in ex_repl:
                                r.state = 'W'

                    #-----------------------------------------------------------
                    # submit for MD within same cycle!

                    replicas_for_md = []
                    for r in replicas:
                        if r.state == 'W':
                            replicas_for_md.append(r)

                    if (len(replicas_for_md) != 0):
                        c_replicas = []
                        for replica in replicas_for_md:
                            cu_name = str(replica.id) + '_' + str(replica.group_idx[dim_int-1])
                            self.logger.info( "cu_name: {0}".format(cu_name) )
                            compute_replica = md_kernel.prepare_replica_for_md(dim_int, dim_str[dim_int], replicas_for_md, replica, self.sd_shared_list)
                            compute_replica.name = cu_name
                            c_replicas.append( compute_replica )
                            
                        sub_replicas = unit_manager.submit_units(c_replicas)
                        sub_md_replicas += sub_replicas

                        for r in replicas_for_md:
                            r.state = 'R'
                        running_replicas += replicas_for_md

                    #-----------------------------------------------------------

            completeddd_cus = []
            completed = 0
            # fist wait
            while ( completed < (len(sub_md_replicas) / 2) ):
                self.logger.info( "proceed when completed replicas >= {0}".format( len(sub_md_replicas) / 2 ) )
                completeddd_cus = []
                for cu in sub_md_replicas:
                    if cu.state == 'Done':
                        completeddd_cus.append(cu)
                time.sleep(1)
                completed = len(completeddd_cus)
                c_end = datetime.datetime.utcnow()
                simulation_time = (c_end - c_start).total_seconds()
                if (simulation_time > self.runtime*60.0):
                    completed = md_kernel.replicas
                   
            # second wait
            no_partner = 1
            while(no_partner == 1):
                all_gr_list = []
                processed_cus = []
                for cu in completeddd_cus:
                    if cu.name not in processed_cus:
                        self.logger.info( "cu_name_2: {0}".format( cu.name ) )
                        r_tuple = cu.name.split('_')
                        self.logger.info( "r_tuple: " )
                        self.logger.info( r_tuple )
                        cu_gr_id = r_tuple[1]
                        gr_list = []
                        gr_list.append(cu.name)
                        processed_cus.append(cu.name)
                        for cu1 in completeddd_cus:
                            if cu.name != cu1.name:
                                self.logger.info( "cu1_name_2: {0}".format( cu1.name ) )
                                r1_tuple = cu1.name.split('_')
                                self.logger.info( "r1_tuple: " )
                                self.logger.info( r1_tuple )
                                cu1_gr_id = r1_tuple[1]
                                if cu_gr_id == cu1_gr_id:
                                    gr_list.append(cu1.name)
                                    processed_cus.append(cu1.name)
                        all_gr_list.append(gr_list)
                print "all_gr_list: "
                print all_gr_list
                all_gr_list_sizes = []
                for gr_list in all_gr_list:
                    all_gr_list_sizes.append( len(gr_list) )
                self.logger.info( "all_gr_list_sizes: " )
                self.logger.info( all_gr_list_sizes )
                # some replica does not have a partner
                if 1 in all_gr_list_sizes:
                    time.sleep(1)
                    completeddd_cus = []
                    for cu in sub_md_replicas:
                        if cu.state == 'Done':
                            completeddd_cus.append(cu)
                else:
                    no_partner = 0

            c_end = datetime.datetime.utcnow()
            simulation_time = (c_end - c_start).total_seconds()
            self.logger.info( "Simulation time: {0}".format( simulation_time ) )

            c += 1
            current_cycle = c / dim_count

            replicas_for_exchange = []
            rm_cus = []
            for cu in sub_md_replicas:
                #print "state is: {0}".format( cu.state )
                if cu.state == 'Done':
                    print "ok md"
                    for r in running_replicas:
                        r_name = str(r.id) + '_' + str(r.group_idx[dim_int-1])
                        if r_name == cu.name:
                            #print "Replica {0} finished MD".format( r.id )
                            self.logger.info( "Replica {0} finished MD".format( r.id ) )
                            replicas_for_exchange.append(r)
                            running_replicas.remove(r)
                            rm_cus.append(cu)
                            r.state = 'M'

            for cu in rm_cus:
                sub_md_replicas.remove(cu)

            