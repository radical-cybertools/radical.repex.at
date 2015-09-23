"""
.. module:: radical.repex.pilot_kernels.pilot_kernel_pattern_b
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
class PilotKernelPatternB(PilotKernel):
    """This class is responsible for performing all Radical Pilot related 
    operations for RE scheme 2.
    This includes pilot launching, running main loop of RE simulation and using 
    RP API for data staging in and out. 

    RE pattern B:
    - Synchronous RE scheme: none of the replicas can start exchange before all 
    replicas has finished MD run.
    Conversely, none of the replicas can start MD run before all replicas has 
    finished exchange step. 
    In other words global barrier is present.   
    - Number of replicas is greater than number of allocated resources for both 
    MD and exchange step.
    - Simulation cycle is defined by the fixed number of simulation time-steps 
    for each replica.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed in decentralized fashion on target resource.
    """
    def __init__(self, inp_file):
        """Constructor.

        Arguments:
        inp_file - json input file with Pilot and NAMD related parameters as 
        specified by user 
        """

        PilotKernel.__init__(self, inp_file)

        self.name = 'pk-patternB'
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
       
        unit_manager = radical.pilot.UnitManager(session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(pilot_object)

        stagein_start = datetime.datetime.utcnow()

        # creating restraint files for US case 
        if md_kernel.name == 'ak-patternB-us':
            for r in replicas:
                md_kernel.build_restraint_file(r)

        # staging shared input data in
        md_kernel.prepare_shared_data()

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

        # bulk = 0: do sequential submission
        # bulk = 1: do bulk submission
        BULK = 0

        for current_cycle in range(1,CYCLES):

            hl_performance_data["cycle_{0}".format(current_cycle)] = {}
            cu_performance_data["cycle_{0}".format(current_cycle)] = {}

            self.logger.info("Performing cycle: {0}".format(current_cycle) )

            self.logger.info("Preparing {0} replicas for MD run; cycle {1}".format(md_kernel.replicas, current_cycle) )

            submitted_replicas = []

            #-------------------------------------------------------------------
            # sequential submission

            outfile = "md_prep_submission_details_{0}.csv".format(session.uid)
            if BULK == 0:
                t1 = datetime.datetime.utcnow()
                for r in replicas:

                    with open(outfile, 'w+') as f:
                        t_1 = datetime.datetime.utcnow()
                        compute_replica = md_kernel.prepare_replica_for_md(r, self.sd_shared_list)
                        t_2 = datetime.datetime.utcnow()
                        value =  (t_2-t_1).total_seconds()
                        f.write("repex_md_prep_time {0}\n".format(value))

                        t_1 = datetime.datetime.utcnow()
                        sub_replica = unit_manager.submit_units(compute_replica)
                        t_2 = datetime.datetime.utcnow()
                        value = (t_2-t_1).total_seconds()
                        f.write("rp_submit_time {0}\n".format(value))

                        submitted_replicas.append(sub_replica)
                f.close()
                t2 = datetime.datetime.utcnow()

            #-------------------------------------------------------------------
            # bulk submision

            else:
                c_replicas = []
                t1 = datetime.datetime.utcnow()

                t_1 = datetime.datetime.utcnow()
                for r in replicas:
                    compute_replica = md_kernel.prepare_replica_for_md(r, self.sd_shared_list)
                    c_replicas.append(compute_replica)
                t_2 = datetime.datetime.utcnow()

                with open(outfile, 'w+') as f:
                    value =  (t_2-t_1).total_seconds()
                    f.write("repex_md_prep_time {0}\n".format(value))

                    t_1 = datetime.datetime.utcnow()
                    submitted_replicas = unit_manager.submit_units(c_replicas)
                    t_2 = datetime.datetime.utcnow()
                    value = (t_2-t_1).total_seconds()
                    f.write("rp_submit_time {0}\n".format(value))
 
                t2 = datetime.datetime.utcnow()
            
            #-------------------------------------------------------------------

            hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("MD_prep")] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("MD_prep")] = (t2-t1).total_seconds()

            self.logger.info("Submitting {0} replicas for MD run; cycle {1}".format(md_kernel.replicas, current_cycle) )
            t1 = datetime.datetime.utcnow()
            #unit_manager.wait_units()
            time.sleep(150)
            t2 = datetime.datetime.utcnow()

            hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("MD")] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("MD")] = (t2-t1).total_seconds()

            cu_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("MD")] = {}
            for cu in submitted_replicas:
                cu_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("MD")]["cu.uid_{0}".format(cu.uid)] = cu

            self.logger.info("Preparing {0} replicas for Exchange run; cycle {1}".format(md_kernel.replicas, current_cycle) )

            exchange_replicas = []

            #-------------------------------------------------------------------
            # 

            t1 = datetime.datetime.utcnow()

            t_1 = datetime.datetime.utcnow()
            ex_replica = md_kernel.prepare_global_ex_calc(current_cycle, replicas, self.sd_shared_list)
            t_2 = datetime.datetime.utcnow()

            with open(outfile, 'a') as f:
                value =  (t_2-t_1).total_seconds()
                f.write("repex_ex_prep_time {0}\n".format(value))
           
                t_1 = datetime.datetime.utcnow()
                exchange_replica = unit_manager.submit_units(ex_replica)
                t_2 = datetime.datetime.utcnow()

                value =  (t_2-t_1).total_seconds()
                f.write("rp_submit_time {0}\n".format(value))

            t2 = datetime.datetime.utcnow()

            #-------------------------------------------------------------------

            hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("EX_prep")] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("EX_prep")] = (t2-t1).total_seconds()

            self.logger.info("Submitting {0} replicas for Exchange run; cycle {1}".format(md_kernel.replicas, current_cycle) )

            t1 = datetime.datetime.utcnow()
            unit_manager.wait_units()
            t2 = datetime.datetime.utcnow()

            hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("EX")] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("EX")] = (t2-t1).total_seconds()

            cu_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("EX")] = {}
            
            cu_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("EX")]["cu.uid_{0}".format(cu.uid)] = exchange_replica

            #-------------------------------------------------------------------
            # post processing

            t1 = datetime.datetime.utcnow()
      
            if exchange_replica.state != radical.pilot.DONE:
                self.logger.error('Exchange step failed for unit:  %s' % exchange_replica.uid)
                
            md_kernel.do_exchange(current_cycle, replicas)

            t2 = datetime.datetime.utcnow()

            hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("Post_processing")] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["run_{0}".format("Post_processing")] = (t2-t1).total_seconds()


            #-------------------------------------------------------------------

            outfile = "execution_profile_{mysession}.csv".format(mysession=session.uid)
            hl_cycle = "cycle_{0}".format(current_cycle)

            with open(outfile, 'a') as f:
                
                head = "Cycle; Step; Duration"
                #print head
                f.write("{row}\n".format(row=head))
                
                for step in hl_performance_data[hl_cycle].keys():
                    duration = hl_performance_data[hl_cycle][step]

                    row = "{Cycle}; {Step}; {Duration}".format(Duration=duration, Cycle=hl_cycle, Step=step)
                    f.write("{r}\n".format(r=row))
                #---------------------------------------------------------------   
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

        with open(outfile, 'a') as f:
            f.write("Total simulaiton time: {row}\n".format(row=raw_simulation_time))
            f.write("Stage-in time: {row}\n".format(row=stagein_time))

        