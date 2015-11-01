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
class PilotKernelPatternS(PilotKernel):
    
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
    def run_simulation(self, replicas, pilot_object, session,  md_kernel ):
        """This function runs the main loop of RE simulation for RE scheme 2a.

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

        #-----------------------------------------------------------------------
        #
        CYCLES = md_kernel.nr_cycles + 1

        do_profile = os.getenv('REPEX_PROFILING', '0')
       
        unit_manager = radical.pilot.UnitManager(session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(pilot_object)

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

            pilot_object.stage_in(sd_pilot)

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
        # bulk = 0: do sequential submission
        # bulk = 1: do bulk submission
        BULK = 1

        for current_cycle in range(1,CYCLES):

            hl_performance_data["cycle_{0}".format(current_cycle)] = {}
            cu_performance_data["cycle_{0}".format(current_cycle)] = {}

            self.logger.info("Performing cycle: {0}".format(current_cycle) )

            self.logger.info("Creating {0} replica tasks for MD-step. cycle {1}".format(md_kernel.replicas, current_cycle) )

            simulation_replicas = []
            exchange_replicas = []

            outfile = "md_prep_submission_details_{0}.csv".format(session.uid)

            self.logger.info("Submitting {0} replica tasks for execution. cycle {1}".format(md_kernel.replicas, current_cycle) )
            #-------------------------------------------------------------------
            # sequential submission
            if not BULK:
                cu_prep = 0.0
                cu_sub = 0.0
                for replica in replicas:
                    t_1 = datetime.datetime.utcnow()
                    compute_replica = md_kernel.prepare_replica_for_md(replica, self.sd_shared_list)
                    t_2 = datetime.datetime.utcnow()
                    cu_prep += (t_2-t_1).total_seconds()
                    t__1 = datetime.datetime.utcnow()
                    s_replica = unit_manager.submit_units(compute_replica)
                    t__2 = datetime.datetime.utcnow()
                    cu_sub += (t__2-t__1).total_seconds()
                    simulation_replicas.append(s_replica)
                
                if do_profile == '1':
                    with open(outfile, 'a') as f:
                        f.write("repex_md_prep_time {0}\n".format(cu_prep))
                        f.write("rp_submit_time {0}\n".format(cu_sub))
              
                hl_performance_data["cycle_{0}".format(current_cycle)]["md_prep"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["md_prep"] = cu_prep

                hl_performance_data["cycle_{0}".format(current_cycle)]["md_sub"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["md_sub"] = cu_sub
                
            #-------------------------------------------------------------------
            # bulk submision
            else:
                cu_prep = 0.0
                cu_sub = 0.0
                c_replicas = []

                t_1 = datetime.datetime.utcnow()
                for replica in replicas:
                    compute_replica = md_kernel.prepare_replica_for_md(replica, self.sd_shared_list)
                    c_replicas.append(compute_replica)
                t_2 = datetime.datetime.utcnow()

                if do_profile == '1':
                    with open(outfile, 'a') as f:
                        cu_prep = (t_2-t_1).total_seconds()
                        f.write("repex_md_prep_time {0}\n".format(cu_prep))

                        t_1 = datetime.datetime.utcnow()
                        simulation_replicas = unit_manager.submit_units(c_replicas)
                        t_2 = datetime.datetime.utcnow()
                        cu_sub = (t_2-t_1).total_seconds()
                        f.write("rp_submit_time {0}\n".format(cu_sub))
                else:
                    simulation_replicas = unit_manager.submit_units(c_replicas)

                hl_performance_data["cycle_{0}".format(current_cycle)]["md_prep"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["md_prep"] = cu_prep

                hl_performance_data["cycle_{0}".format(current_cycle)]["md_sub"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["md_sub"] = cu_sub
 
            if (md_kernel.ex_name == 'salt-concentration') or (md_kernel.exchange_mpi == False):

                t1 = datetime.datetime.utcnow()
                unit_manager.wait_units()
                t2 = datetime.datetime.utcnow()

                hl_performance_data["cycle_{0}".format(current_cycle)]["md_run"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["md_run"] = (t2-t1).total_seconds()

                cu_performance_data["cycle_{0}".format(current_cycle)]["md_run"] = {}
                for cu in simulation_replicas:
                    cu_performance_data["cycle_{0}".format(current_cycle)]["md_run"]["cu.uid_{0}".format(cu.uid)] = cu

                if not BULK:
                    #-----------------------------------------------------------
                    # sequential submission
                    cu_prep = 0.0
                    cu_sub = 0.0
                    for replica in replicas:
                        t_1 = datetime.datetime.utcnow()
                        ex_replica = md_kernel.prepare_replica_for_exchange(replicas, replica, self.sd_shared_list)
                        t_2 = datetime.datetime.utcnow()
                        cu_prep += (t_2-t_1).total_seconds()
                        t__1 = datetime.datetime.utcnow()
                        e_replica = unit_manager.submit_units(ex_replica)
                        t__2 = datetime.datetime.utcnow()
                        cu_sub += (t__2-t__1).total_seconds()
                        exchange_replicas.append(s_replica)

                    if do_profile == '1':
                        with open(outfile, 'a') as f:
                            f.write("repex_ind_ex_prep_time {0}\n".format(cu_prep))
                            f.write("rp_ind_ex_submit_time {0}\n".format(cu_sub))
              
                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_prep"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_prep"] = cu_prep

                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_sub"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_sub"] = cu_sub
                    t1 = datetime.datetime.utcnow()
                else:
                    #-----------------------------------------------------------
                    # bulk submission
                    cu_prep = 0.0
                    cu_sub = 0.0
                    e_replicas = []
                    t_1 = datetime.datetime.utcnow()
                    for replica in replicas:
                        ex_replica = md_kernel.prepare_replica_for_exchange(replicas, replica, self.sd_shared_list)
                        e_replicas.append(ex_replica)
                    t_2 = datetime.datetime.utcnow()
                    cu_prep =  (t_2-t_1).total_seconds()

                    if do_profile == '1':
                        with open(outfile, 'a') as f:
                            f.write("repex_ind_ex_prep_time {0}\n".format(cu_prep))
                            t_1 = datetime.datetime.utcnow()
                            exchange_replicas = unit_manager.submit_units(e_replicas)
                            t_2 = datetime.datetime.utcnow()
                            cu_sub = (t_2-t_1).total_seconds()
                            f.write("rp_ind_ex_submit_time {0}\n".format(cu_sub))
                    else:
                        exchange_replicas = unit_manager.submit_units(e_replicas)

                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_prep"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_prep"] = cu_prep

                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_sub"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_sub"] = cu_sub
                    t1 = datetime.datetime.utcnow()
                #---------------------------------------------------------------
                
                unit_manager.wait_units()
                t2 = datetime.datetime.utcnow()

                hl_performance_data["cycle_{0}".format(current_cycle)]["ex_run"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["ex_run"] = (t2-t1).total_seconds()

                cu_performance_data["cycle_{0}".format(current_cycle)]["ex_run"] = {}
                for cu in exchange_replicas:
                    cu_performance_data["cycle_{0}".format(current_cycle)]["ex_run"]["cu.uid_{0}".format(cu.uid)] = cu
                
                #---------------------------------------------------------------
                # submitting unit which determines exchanges between replicas
                if GL == 1:
                    t_1 = datetime.datetime.utcnow()
                    ex_calculator = md_kernel.prepare_global_ex_calc(GL, current_cycle, replicas, self.sd_shared_list)
                    t_2 = datetime.datetime.utcnow()

                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_prep_global"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_prep_global"] = (t_2-t_1).total_seconds()

                    t1 = datetime.datetime.utcnow()
                    global_ex_cu = unit_manager.submit_units(ex_calculator)
                    t2 = datetime.datetime.utcnow()
                    cu_sub = (t2-t1).total_seconds()

                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_sub_global"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_sub_global"] = cu_sub

                    t1 = datetime.datetime.utcnow()
                    unit_manager.wait_units()
                    t2 = datetime.datetime.utcnow()

                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_run_global"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_run_global"] = (t2-t1).total_seconds()

                    cu_performance_data["cycle_{0}".format(current_cycle)]["ex_run_global"] = {}
                    cu_performance_data["cycle_{0}".format(current_cycle)]["ex_run_global"]["cu.uid_{0}".format(global_ex_cu.uid)] = global_ex_cu

            else:
                t1 = datetime.datetime.utcnow()
                unit_manager.wait_units()
                t2 = datetime.datetime.utcnow()

                hl_performance_data["cycle_{0}".format(current_cycle)]["md_run"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["md_run"] = (t2-t1).total_seconds()

                cu_performance_data["cycle_{0}".format(current_cycle)]["md_run"] = {}
                for cu in simulation_replicas:
                    cu_performance_data["cycle_{0}".format(current_cycle)]["md_run"]["cu.uid_{0}".format(cu.uid)] = cu

                #---------------------------------------------------------------
                # submitting unit which determines exchanges between replicas
                if GL == 1:

                    self.logger.info("Generating exchange tasks for Exchange-step. cycle {0}".format(current_cycle) )
                    t_1 = datetime.datetime.utcnow()
                    ex_calculator = md_kernel.prepare_global_ex_calc(GL, current_cycle, replicas, self.sd_shared_list)
                    t_2 = datetime.datetime.utcnow()
                    
                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_prep_global"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_prep_global"] = (t_2-t_1).total_seconds()

                    self.logger.info("Submitting exchange tasks for execution. cycle {0}".format(current_cycle) )
                    t1 = datetime.datetime.utcnow()
                    global_ex_cu = unit_manager.submit_units(ex_calculator)
                    t2 = datetime.datetime.utcnow()
                    cu_sub = (t2-t1).total_seconds()

                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_sub_global"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_sub_global"] = cu_sub

                    t1 = datetime.datetime.utcnow()
                    unit_manager.wait_units()
                    t2 = datetime.datetime.utcnow()

                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_run_global"] = {}
                    hl_performance_data["cycle_{0}".format(current_cycle)]["ex_run_global"] = (t2-t1).total_seconds()

                    cu_performance_data["cycle_{0}".format(current_cycle)]["ex_run_global"] = {}
                    cu_performance_data["cycle_{0}".format(current_cycle)]["ex_run_global"]["cu.uid_{0}".format(global_ex_cu.uid)] = global_ex_cu

            #-------------------------------------------------------------------
            # post processing

            t1 = datetime.datetime.utcnow()
      
            if global_ex_cu.state != radical.pilot.DONE:
                self.logger.error('Exchange step failed for unit:  %s' % global_ex_cu.uid)
                
            self.logger.info("Exchanging replica configurations. cycle {0}".format(current_cycle) )
            md_kernel.do_exchange(current_cycle, replicas)

            t2 = datetime.datetime.utcnow()

            hl_performance_data["cycle_{0}".format(current_cycle)]["post_proc"] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["post_proc"] = (t2-t1).total_seconds()

            #-------------------------------------------------------------------

            outfile = "execution_profile_{mysession}.csv".format(mysession=session.uid)
            hl_cycle = "cycle_{0}".format(current_cycle)

            if do_profile == '1':
                with open(outfile, 'a') as f:
                    
                    head = "Cycle; Step; Duration"
                    #print head
                    f.write("{row}\n".format(row=head))
                    
                    for step in hl_performance_data[hl_cycle].keys():
                        duration = hl_performance_data[hl_cycle][step]

                        row = "{Cycle}; {Step}; {Duration}".format(Duration=duration, Cycle=hl_cycle, Step=step)
                        f.write("{r}\n".format(r=row))
                    #-----------------------------------------------------------
                    head = "CU_ID; Scheduling; StagingInput; Allocating; Executing; StagingOutput; Done; Cycle; Step;"
                    f.write("{row}\n".format(row=head))
                
                    for step in cu_performance_data[hl_cycle].keys():
                        for cid in cu_performance_data[hl_cycle][step].keys():
                            cu = cu_performance_data[hl_cycle][step][cid]
                            st_data = {}
                            for st in cu.state_history:
                                st_dict = st.as_dict()
                                st_data["{0}".format( st_dict["state"] )] = {}
                                st_data["{0}".format( st_dict["state"] )] = st_dict["timestamp"]

                            if 'StagingOutput' not in st_data:
                                st_data['StagingOutput'] = st_data['Executing']

                            if 'Done' not in st_data:
                                st_data['Done'] = st_data['Executing']

                            row = "{uid}; {Scheduling}; {StagingInput}; {Allocating}; {Executing}; {StagingOutput}; {Done}; {Cycle}; {Step}".format(
                                uid=cu.uid,
                                Scheduling=(st_data['Scheduling']),
                                StagingInput=(st_data['StagingInput']),
                                Allocating=(st_data['Allocating']),
                                Executing=(st_data['Executing']),
                                StagingOutput=(st_data['StagingOutput']),
                                Done=(st_data['Done']),
                                Cycle=hl_cycle,
                                Step=step)
                        
                            f.write("{r}\n".format(r=row))

            #-------------------------------------------------------------------
            # end of loop

        end = datetime.datetime.utcnow()
        raw_simulation_time = (end-start).total_seconds()
        stagein_time = (stagein_end-stagein_start).total_seconds()
        outfile = "execution_profile_{mysession}.csv".format(mysession=session.uid)

        if do_profile == '1':
            with open(outfile, 'a') as f:
                f.write("Total simulaiton time: {row}\n".format(row=raw_simulation_time))
                f.write("Stage-in time: {row}\n".format(row=stagein_time))

        