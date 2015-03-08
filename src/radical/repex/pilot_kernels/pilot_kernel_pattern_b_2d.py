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

class PilotKernelPatternB2d(PilotKernel):
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

        self.name = 'pk-patternB-2d'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        self.sd_shared_list = []

#-----------------------------------------------------------------------------------------------------------------------------------
    def getkey(self, item):
        return item[0]


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
                swap_matrix[i][r.id] = float(matrix_columns[r.id][i])

            # setting old_path and first_path for each replica
            if ( r.cycle == 1 ):
                r.first_path = matrix_columns[r.id][len(replicas)]
                r.old_path = matrix_columns[r.id][len(replicas)]
            else:
                r.old_path = matrix_columns[r.id][len(replicas)]

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
            
            self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )

            if state == radical.pilot.states.FAILED:
                
                self.logger.error("Log: {0:s}".format( unit.as_dict() ) )
                # restarting the replica
                #self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )
                #unit_manager.submit_units( unit.description )
                
        unit_manager = radical.pilot.UnitManager(session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(pilot_object)

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
                         'action': radical.pilot.LINK
            }
            self.sd_shared_list.append(sd_shared)

        # make sure data is staged
        time.sleep(10)

        # for performance data collection
        hl_performance_data = {}
        cu_performance_data = {}

        #------------------------
        # Raw simulation time
        start = datetime.datetime.utcnow()
        #------------------------

        for r in replicas:
            self.logger.debug("Replica: id={0} salt={1} temperature={2}".format(r.id, r.new_salt_concentration, r.new_temperature) )

        t1 = datetime.datetime.utcnow()
        md_kernel.init_matrices(replicas)
        t2 = datetime.datetime.utcnow()

        matrix_init_time = (t2-t1).total_seconds()
        

        for i in range(md_kernel.nr_cycles):
            #-------------------------------------------------------------------------------
            # D1 run (temperature exchange)
            D = 1
            current_cycle = i+1

            cu_performance_data["cycle_{0}".format(current_cycle)] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)] = {}
           
            self.logger.info("Performing cycle: {0}".format(current_cycle) )
            
            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)] = {}

            self.logger.info("Dim 1: preparing {0} replicas for MD run; cycle {1}".format(md_kernel.replicas, current_cycle) )
            
            t1 = datetime.datetime.utcnow()
            compute_replicas = md_kernel.prepare_replicas_for_md(replicas, self.sd_shared_list)
            t2 = datetime.datetime.utcnow()

            self.logger.info("Dim 1: submitting {0} replicas for MD run; cycle {1}".format(md_kernel.replicas, current_cycle) )

            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["MD_prep"] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["MD_prep"] = (t2-t1).total_seconds()

            t1 = datetime.datetime.utcnow()
            submitted_replicas = unit_manager.submit_units(compute_replicas)
            unit_manager.wait_units()
            t2 = datetime.datetime.utcnow()
            
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["MD_run"] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["MD_run"] = (t2-t1).total_seconds()


            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["run_{0}".format("MD")] = {}
            for cu in submitted_replicas:
                cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["run_{0}".format("MD")]["cu.uid_{0}".format(cu.uid)] = cu

            
            # this is not done for the last cycle
            if (i != (md_kernel.nr_cycles-1)):
                
                self.logger.info("Dim 1: preparing {0} replicas for Exchange run; cycle {1}".format(md_kernel.replicas, current_cycle) )

                t1 = datetime.datetime.utcnow()
                exchange_replicas = md_kernel.prepare_replicas_for_exchange(D, replicas, self.sd_shared_list)
                t2 = datetime.datetime.utcnow()

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["EX_prep"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["EX_prep"] = (t2-t1).total_seconds()

                self.logger.info("Dim 1: submitting {0} replicas for Exchange run; cycle {1}".format(md_kernel.replicas, current_cycle) )

                t1 = datetime.datetime.utcnow()
                submitted_replicas = unit_manager.submit_units(exchange_replicas)
                unit_manager.wait_units()
                t2 = datetime.datetime.utcnow()
             
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["EX_run"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["EX_run"] = (t2-t1).total_seconds()


                cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["run_{0}".format("EX")] = {}
                for cu in submitted_replicas:
                    cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["run_{0}".format("EX")]["cu.uid_{0}".format(cu.uid)] = cu

                
                t1 = datetime.datetime.utcnow()
                matrix_columns = []
                for r in submitted_replicas:
                    d = str(r.stdout)
                    data = d.split()
                    matrix_columns.append(data)

                self.logger.info("Dim 1: composing swap matrix from individual files for all replicas")
                swap_matrix = self.compose_swap_matrix(replicas, matrix_columns)
            
                self.logger.info("Dim 1: performing exchange")
                md_kernel.select_for_exchange(D, replicas, swap_matrix, current_cycle)

                t2 = datetime.datetime.utcnow()

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["Post_proc"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["Post_proc"] = (t2-t1).total_seconds()

            #---------------------------------------------
            # D2 run (salt concentration exchange)
            D = 2
            t1 = datetime.datetime.utcnow() 

            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)] = {}
 
            self.logger.info("Dim 2: preparing {0} replicas for MD run; cycle {1}".format(md_kernel.replicas, current_cycle) )
            
            compute_replicas = md_kernel.prepare_replicas_for_md(replicas, self.sd_shared_list)

            self.logger.info("Dim 2: submitting {0} replicas for MD run; cycle {1}".format(md_kernel.replicas, current_cycle) )

            t2 = datetime.datetime.utcnow()

            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["MD_prep"] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["MD_prep"] = (t2-t1).total_seconds()

            t1 = datetime.datetime.utcnow()
            submitted_replicas = unit_manager.submit_units(compute_replicas)
            unit_manager.wait_units()
            t2 = datetime.datetime.utcnow()

            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["MD_run"] = {}
            hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["MD_run"] = (t2-t1).total_seconds()

            cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["run_{0}".format("MD")] = {}
            for cu in submitted_replicas:
                cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["run_{0}".format("MD")]["cu.uid_{0}".format(cu.uid)] = cu

            
            # this is not done for the last cycle
            if (i != (md_kernel.nr_cycles-1)):
               
                self.logger.info("Dim 2: preparing {0} replicas for Exchange run; cycle {1}".format(md_kernel.replicas, current_cycle) )

                t1 = datetime.datetime.utcnow()
                exchange_replicas = md_kernel.prepare_replicas_for_exchange(D, replicas, self.sd_shared_list)
                t2 = datetime.datetime.utcnow()

                self.logger.info("Dim 2: submitting {0} replicas for Exchange run; cycle {1}".format(md_kernel.replicas, current_cycle) )

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["EX_prep"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["EX_prep"] = (t2-t1).total_seconds()

                t1 = datetime.datetime.utcnow()
                submitted_replicas = unit_manager.submit_units(exchange_replicas)
                unit_manager.wait_units()
                t2 = datetime.datetime.utcnow()

                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["EX_run"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["EX_run"] = (t2-t1).total_seconds()

                cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["run_{0}".format("EX")] = {}
                for cu in submitted_replicas:
                    cu_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["run_{0}".format("EX")]["cu.uid_{0}".format(cu.uid)] = cu


                t1 = datetime.datetime.utcnow()
                matrix_columns = []
                for r in submitted_replicas:
                    d = str(r.stdout)
                    data = d.split()
                    matrix_columns.append(data)
                
                self.logger.info("Dim 2: Composing swap matrix from individual files for all replicas")
                swap_matrix = self.compose_swap_matrix(replicas, matrix_columns)
            
                self.logger.info("Dim 2: Performing exchange of salt concentrations")
                md_kernel.select_for_exchange(D, replicas, swap_matrix, current_cycle)

                t2 = datetime.datetime.utcnow()
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["Post_proc"] = {}
                hl_performance_data["cycle_{0}".format(current_cycle)]["dim_{0}".format(D)]["Post_proc"] = (t2-t1).total_seconds()

                
        # end of loop
        d1_id_matrix = md_kernel.get_d1_id_matrix()
        temp_matrix = md_kernel.get_temp_matrix()
        
        d2_id_matrix = md_kernel.get_d2_id_matrix()
        salt_matrix = md_kernel.get_salt_matrix()

        self.logger.debug("Exchange matrix of replica id's for Dim 1 (temperature) exchange: {0:s}".format(d1_id_matrix) )
         
        self.logger.debug("Change in temperatures for each replica: : {0:s}".format(temp_matrix) )
       
        self.logger.debug("Exchange matrix of replica id's for Dim 2 (salt concentration) exchange: {0:s}".format(d2_id_matrix) )

        self.logger.debug("Change in salt concentration for each replica: {0:s}".format(salt_matrix) )
       
        #------------------------------------------------
        # performance data
        outfile = "execution_profile_{time}.csv".format(time=datetime.datetime.now().isoformat())
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
                                New= (st_data['New']-start).total_seconds(),
                                exestart=(cu.start_time-start).total_seconds(),
                                exestop=(cu.stop_time-start).total_seconds(),
                                Done=(st_data['Done']-start).total_seconds(),
                                Cycle=cycle,
                                Dim=dim,
                                Run=run)
                        
                            #print row
                            f.write("{r}\n".format(r=row))

            """
            #------------------------------------------------------------
            # this is for graph
            head = "New1; New2; exestart1; exestart2; exeEnd1; exeEnd2; Done1; Done2; Cycle; Dim; Run"

            f.write("{row}\n".format(row=head))

            for cycle in cu_performance_data:
                for dim in cu_performance_data[cycle].keys():
                    for run in cu_performance_data[cycle][dim].keys():
                        new_list = []
                        exestart_list = []
                        exestop_list = []
                        done_list = [] 
                        for cid in cu_performance_data[cycle][dim][run].keys():
                            cu = cu_performance_data[cycle][dim][run][cid]
                            st_data = {}
                            for st in cu.state_history:
                                st_dict = st.as_dict()
                                st_data["{0}".format( st_dict["state"] )] = {}
                                st_data["{0}".format( st_dict["state"] )] = st_dict["timestamp"]

                            new_list.append( (st_data['New']-start).total_seconds()  )
                            exestart_list.append( (cu.start_time-start).total_seconds()  )
                            exestop_list.append( (cu.stop_time-start).total_seconds()  )
                            done_list.append( (st_data['Done']-start).total_seconds()  )
                        
                        row = "{New1}; {New2}; {exestart1}; {exestart2}; {exestop1}; {exestop2}; {Done1}; {Done2}; {Cycle}; {Dim}; {Run}".format(
                            New1= min(new_list),
                            New2= max(new_list),
                            exestart1=min(exestart_list),
                            exestart2=max(exestart_list), 
                            exestop1=min(exestop_list),
                            exestop2=max(exestop_list),
                            Done1=min(done_list),
                            Done2=max(done_list),
                            Cycle=cycle,
                            Dim=dim,
                            Run=run)

                        #print row
                        f.write("{r}\n".format(r=row))

            """
                    
        #-------------------------------
        # TIMINGS BY STATE
        #-------------------------------
        """
        head = "CU_ID; New; StagingInput; PendingExecution; Scheduling; Executing; StagingOutput1; StagingOutput2; Done; Cycle; Dim; Run"
        print head

        for cycle in cu_performance_data:
            for dim in cu_performance_data[cycle].keys():  
                for run in cu_performance_data[cycle][dim].keys():
                    for cid in cu_performance_data[cycle][dim][run].keys():
                        cu = cu_performance_data[cycle][dim][run][cid]
                        st_data = {}
                        for st in cu.state_history:
                            st_dict = st.as_dict()
                            if (st_dict["state"] != 'StagingOutput'):
                                st_data["{0}".format( st_dict["state"] )] = {}
                                st_data["{0}".format( st_dict["state"] )] = st_dict["timestamp"]
                            else:
                                if "StagingOutput1" in st_data:
                                    st_data["StagingOutput2"] = {}
                                    st_data["StagingOutput2"] = st_dict["timestamp"]
                                else:
                                    st_data["StagingOutput1"] = {}
                                    st_data["StagingOutput1"] = st_dict["timestamp"]

                        if run == 'run_MD':      
                            row = "{uid}; {New}; {StagingInput}; {PendingExecution}; {Scheduling}; {Executing}; {StagingOutput1}; {StagingOutput2}; {Done}; {Cycle}; {Dim}; {Run}".format(
                                uid=cu.uid,
                                New= (st_data['New']-start).total_seconds(),
                                StagingInput=(st_data['StagingInput']-start).total_seconds(),
                                PendingExecution=(st_data['PendingExecution']-start).total_seconds(),
                                Scheduling=(st_data['Scheduling']-start).total_seconds(),
                                Executing=(st_data['Executing']-start).total_seconds(),
                                StagingOutput1=(st_data['StagingOutput1']-start).total_seconds(),
                                StagingOutput2=(st_data['StagingOutput2']-start).total_seconds(),
                                Done=(st_data['Done']-start).total_seconds(),
                                Cycle=cycle,
                                Dim=dim,
                                Run=run)

                            print row
                        else:
                            row = "{uid}; {New}; {StagingInput}; {PendingExecution}; {Scheduling}; {Executing}; {Done}; {Cycle}; {Dim}; {Run}".format(
                                uid=cu.uid,
                                New=(st_data['New']-start).total_seconds(),
                                StagingInput=(st_data['StagingInput']-start).total_seconds(),
                                PendingExecution=(st_data['PendingExecution']-start).total_seconds(),
                                Scheduling=(st_data['Scheduling']-start).total_seconds(),
                                Executing=(st_data['Executing']-start).total_seconds(),
                                Done=(st_data['Done']-start).total_seconds(),
                                Cycle=cycle,
                                Dim=dim,
                                Run=run)

                            print row
                            
        
        for cycle in cu_performance_data:
            for dim in cu_performance_data[cycle].keys():  
                for run in cu_performance_data[cycle][dim].keys():
                    for cid in cu_performance_data[cycle][dim][run].keys():
                        cu = cu_performance_data[cycle][dim][run][cid]
                        st_data = {}
                        for st in cu.state_history:
                            st_dict = st.as_dict()
                            if (st_dict["state"] != 'StagingOutput'):
                                st_data["{0}".format( st_dict["state"] )] = {}
                                st_data["{0}".format( st_dict["state"] )] = st_dict["timestamp"]
                            else:
                                if "StagingOutput1" in st_data:
                                    st_data["StagingOutput2"] = {}
                                    st_data["StagingOutput2"] = st_dict["timestamp"]
                                else:
                                    st_data["StagingOutput1"] = {}
                                    st_data["StagingOutput1"] = st_dict["timestamp"]

                        if run == 'run_MD':      
                            row = "{uid}; {New}; {StagingInput}; {PendingExecution}; {Scheduling}; {Executing}; {StagingOutput1}; {StagingOutput2}; {Done}; {Cycle}; {Dim}; {Run}".format(
                                uid=cu.uid,
                                New= st_data['New'],
                                StagingInput=st_data['StagingInput'],
                                PendingExecution=st_data['PendingExecution'],
                                Scheduling=st_data['Scheduling'],
                                Executing=st_data['Executing'],
                                StagingOutput1=st_data['StagingOutput1'],
                                StagingOutput2=st_data['StagingOutput2'],
                                Done=st_data['Done'],
                                Cycle=cycle,
                                Dim=dim,
                                Run=run)

                            print row
                        else:
                            row = "{uid}; {New}; {StagingInput}; {PendingExecution}; {Scheduling}; {Executing}; {Done}; {Cycle}; {Dim}; {Run}".format(
                                uid=cu.uid,
                                New= st_data['New'],
                                StagingInput=st_data['StagingInput'],
                                PendingExecution=st_data['PendingExecution'],
                                Scheduling=st_data['Scheduling'],
                                Executing=st_data['Executing'],
                                Done=st_data['Done'],
                                Cycle=cycle,
                                Dim=dim,
                                Run=run)

                            print row
                            """


