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
from pilot_kernels.pilot_kernel import *
import radical.utils.logger as rul

#-----------------------------------------------------------------------------------------------------------------------------------

class PilotKernelPatternBmultiD(PilotKernel):
    """This class is responsible for performing all Radical Pilot related operations for RE pattern B.
    This includes pilot launching, running main loop of RE simulation and using RP API for data staging in and out. 

    RE pattern B:
    - Synchronous RE scheme: none of the replicas can start exchange before all replicas has finished MD run.
    Conversely, none of the replicas can start MD run before all replicas has finished exchange step. 
    In other words global barrier is present.   
    - Number of replicas is greater than number of allocated resources for both MD and exchange step.
    - Simulation cycle is defined by the fixed number of simulation time-steps for each replica.
    - Exchange probabilities are determined using Gibbs sampling.
    - Exchange step is performed in decentralized fashion on target resource.
    """
    def __init__(self, inp_file):
        """Constructor.

        Arguments:
        inp_file - json input file with Pilot and NAMD related parameters as specified by user 
        """
        PilotKernel.__init__(self, inp_file)

        self.name = 'pk-patternB-multiD'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        self.sd_shared_list = []

#-----------------------------------------------------------------------------------------------------------------------------------
    def getkey(self, item):
        return item[0]


    #---------------------------------------------------------
    #
    def build_swap_matrix(self, replicas):
        """Creates a swap matrix from matrix_column_x.dat files. 
        matrix_column_x.dat - is populated on targer resource and then transferred back. This
        file is created for each replica and has data for one column of swap matrix. In addition to that,
        this file holds path to pilot compute unit of the previous run, where reside NAMD output files for 
        a given replica. 

        Arguments:
        replicas - list of Replica objects

        Returns:
        swap_matrix - 2D list of lists of dimension-less energies, where each column is a replica 
        and each row is a state
        """

        base_name = "matrix_column"

        # init matrix
        swap_matrix = [[ 0. for j in range(len(replicas))]
             for i in range(len(replicas))]

        for r in replicas:
            column_file = base_name + "_" + str(r.cycle-1) + "_" + str(r.id) +  ".dat"       
            try:
                f = open(column_file)
                lines = f.readlines()
                f.close()
                data = lines[0].split()
                # populating one column at a time
                for i in range(len(replicas)):
                    swap_matrix[i][r.id] = float(data[i])

            except:
                raise

        return swap_matrix

    #----------------------------------------------------------------------------
    #
    def compose_swap_matrix(self, replicas, matrix_columns):
        """Creates a swap matrix from matrix_column_x.dat files. 
        matrix_column_x.dat - is populated on targer resource and then transferred back. This
        file is created for each replica and has data for one column of swap matrix. In addition to that,
        this file holds path to pilot compute unit of the previous run, where reside NAMD output files for 
        a given replica. 

        Arguments:
        replicas - list of Replica objects

        Returns:
        swap_matrix - 2D list of lists of dimension-less energies, where each column is a replica 
        and each row is a state
        """
 
        # init matrix
        swap_matrix = [[ 0. for j in range(len(replicas))] 
             for i in range(len(replicas))]

        matrix_columns = sorted(matrix_columns)

        for r in replicas:
            # populating one column at a time
            for i in range(len(replicas)):
                # error here: ValueError: could not convert string to float: None
                swap_matrix[i][r.id] = float(matrix_columns[r.id][i])

        return swap_matrix

#-----------------------------------------------------------------------------------------------------------------------------------

    def run_simulation(self, replicas, pilot_object, session,  md_kernel):
        """This function runs the main loop of RE simulation for RE pattern B.

        Arguments:
        replicas - list of Replica objects
        pilot_object - radical.pilot.ComputePilot object
        session - radical.pilot.session object, the *root* object for all other RADICAL-Pilot objects 
        md_kernel - an instance of NamdKernelScheme2a class
        """

        # --------------------------------------------------------------------------
        #
        def unit_state_change_cb(unit, state):
            """This is a callback function. It gets called very time a ComputeUnit changes its state.
            """

            if unit:            
                self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )

                if state == radical.pilot.states.FAILED:
                    self.logger.error("Log: {0:s}".format( unit.as_dict() ) )
                    # restarting the replica
                    #self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )
                    #unit_manager.submit_units( unit.description )

        # --------------------------------------------------------------------------
        cycles = md_kernel.nr_cycles + 1
                
        unit_manager = radical.pilot.UnitManager(session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(pilot_object)

        # creating restraint files for QMMM
        if md_kernel.name == 'ak-patternB-3d':
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
        time.sleep(10)

        # for performance data collection
        hl_performance_data = {}
        cu_performance_data = {}

        md_kernel.init_matrices(replicas)

        #------------------------
        # Raw simulation time
        start = datetime.datetime.utcnow()
        #------------------------

        D = 0
        dimensions = md_kernel.dims
        for c in range(0,cycles*dimensions):
            #-------------------------------------------------------------------------------
            # 
            if D < dimensions:
                D = D + 1
            else:
                D = 1

            current_cycle = c / dimensions

            if D == 1:
                cu_performance_data["cycle_{0}".format(current_cycle)] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)] = {}
                self.logger.info("Performing cycle: {0}".format(current_cycle) )
            
            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)] = {}

            self.logger.info("Dim {0}: preparing {1} replicas for MD run; cycle {2}".format(D, md_kernel.replicas, current_cycle) )
            submitted_replicas = []            

            t1 = datetime.datetime.utcnow()
            for replica in replicas:
                comp_repl = md_kernel.prepare_replica_for_md(replica, self.sd_shared_list)
                sub_repl = unit_manager.submit_units(comp_repl)
                submitted_replicas.append(sub_repl)
            t2 = datetime.datetime.utcnow()

            self.logger.info("Dim {0}: submitting {1} replicas for MD run; cycle {2}".format(D, md_kernel.replicas, current_cycle) )

            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["MD_prep"] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["MD_prep"] = (t2-t1).total_seconds()

            t1 = datetime.datetime.utcnow()
            unit_manager.wait_units()
            t2 = datetime.datetime.utcnow()
            
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["MD_run"] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["MD_run"] = (t2-t1).total_seconds()

            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["run_{0}".format("MD")] = {}
            for cu in submitted_replicas:
                cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["run_{0}".format("MD")]["cu.uid_{0}".format(cu.uid)] = cu
            
            # this is not done for the last cycle
            if (current_cycle < (cycles-1)):
                exchange_replicas = []
                self.logger.info("Dim {0}: preparing {1} replicas for Exchange run; cycle {2}".format(D, md_kernel.replicas, current_cycle) )

                md_kernel.prepare_lists(replicas)

                t1 = datetime.datetime.utcnow()
                for replica in replicas:
                    ex_repl = md_kernel.prepare_replica_for_exchange(D, replicas, replica, self.sd_shared_list)
                    sub_repl = unit_manager.submit_units(ex_repl)
                    exchange_replicas.append(sub_repl)
                t2 = datetime.datetime.utcnow()

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["EX_prep"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["EX_prep"] = (t2-t1).total_seconds()

                self.logger.info("Dim {0}: submitting {1} replicas for Exchange run; cycle {2}".format(D, md_kernel.replicas, current_cycle) )

                t1 = datetime.datetime.utcnow()
                unit_manager.wait_units()
                t2 = datetime.datetime.utcnow()
             
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["EX_run"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["EX_run"] = (t2-t1).total_seconds()

                cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["run_{0}".format("EX")] = {}
                for cu in exchange_replicas:
                    cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["run_{0}".format("EX")]["cu.uid_{0}".format(cu.uid)] = cu

                # populating swap matrix                
                t1 = datetime.datetime.utcnow()

                for r in exchange_replicas:
                    if r.state != radical.pilot.DONE:
                        self.logger.error('ERROR: In D%d exchange step failed for unit:  %s' % (D, r.uid))

                matrix_columns = self.build_swap_matrix(replicas)
 
                # writing swap matrix out
                sw_file = "swap_matrix_" + str(D) + "_" + str(current_cycle)
                try:
                    w_file = open( sw_file, "w")
                    for i in matrix_columns:
                        for j in i:
                            w_file.write("%s " % j)
                        w_file.write("\n")
                    w_file.close()
                except IOError:
                    self.logger.info('Warning: unable to access file %s' % sw_file)
            
                self.logger.info("Dim {0}: performing exchange".format(D))
                md_kernel.select_for_exchange(D, replicas, matrix_columns, current_cycle)

                t2 = datetime.datetime.utcnow()

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["Post_proc"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["Post_proc"] = (t2-t1).total_seconds()
            
        #--------------------------------------------------------------------------------------------------------------------------
        # end of loop

        #------------------------------------------------
        # performance data
        outfile = "execution_profile_{mysession}.csv".format(mysession=session.uid)
        with open(outfile, 'w+') as f:
            #------------------------
            # RAW SIMULATION TIME
            end = datetime.datetime.utcnow()
            #------------------------
            RAW_SIMULATION_TIME = (end-start).total_seconds()
            #print "RAW_SIMULATION_TIME: %f" % RAW_SIMULATION_TIME
            f.write("RAW_SIMULATION_TIME: {row}\n".format(row=RAW_SIMULATION_TIME))

            #------------------------------------------------------------
            #
            head = "Cycle; Dim; Run; Duration"
            #print head
            f.write("{row}\n".format(row=head))

            for cycle in hl_performance_data:
                for dim in hl_performance_data[cycle].keys():
                    for run in hl_performance_data[cycle][dim].keys():
                        dur = hl_performance_data[cycle][dim][run]

                        row = "{Cycle}; {Dim}; {Run}; {Duration}".format(
                            Duration=dur,
                            Cycle=cycle,
                            Dim=dim,
                            Run=run)

                        #print row
                        f.write("{r}\n".format(r=row))

            
            #------------------------------------------------------------
            # these timings are measured from simulation start!
            head = "CU_ID; New; exestart; exeEnd; Done; Cycle; Dim; Run"
            #print head
            f.write("{row}\n".format(row=head))
            """
            for cycle in cu_performance_data:
                for dim in cu_performance_data[cycle].keys():
                    for run in cu_performance_data[cycle][dim].keys():
                        for cid in cu_performance_data[cycle][dim][run].keys():
                            cu = cu_performance_data[cycle][dim][run][cid]
                            st_data = {}
                            for st in cu.state_history:
                                st_dict = st.as_dict()
                                st_data["{0}".format( st_dict["state"] )] = {}
                                st_data["{0}".format( st_dict["state"] )] = st_dict["timestamp"]

                            row = "{uid}; {New}; {exestart}; {exestop}; {Done}; {Cycle}; {Dim}; {Run}".format(
                                uid=cu.uid,
                                New= (st_data['Unscheduled']-start).total_seconds(),
                                exestart=(cu.start_time-start).total_seconds(),
                                exestop=(cu.stop_time-start).total_seconds(),
                                Done=(st_data['Done']-start).total_seconds(),
                                Cycle=cycle,
                                Dim=dim,
                                Run=run)
                        
                            #print row
                            f.write("{r}\n".format(r=row))
            """

