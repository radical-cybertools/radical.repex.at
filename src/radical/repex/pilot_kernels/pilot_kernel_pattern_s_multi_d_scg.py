"""
.. module:: radical.repex.pilot_kernels.pilot_kernel_pattern_s_multi_d_sc
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

class PilotKernelPatternSmultiDscg(PilotKernel):
    """
    """
    def __init__(self, inp_file, rconfig):
        """Constructor.

        Arguments:
        inp_file - json input file with Pilot and NAMD related parameters as 
        specified by user 
        """
        PilotKernel.__init__(self, inp_file, rconfig)

        self.name = 'exec-pattern-A-multiDsc'
        self.logger  = rul.getLogger ('radical.repex', self.name)

        self.sd_shared_list = []

#-------------------------------------------------------------------------------

    def run_simulation(self, replicas, md_kernel):
        """This function runs the main loop of RE simulation for RE pattern B.

        Arguments:
        replicas - list of Replica objects
        md_kernel - an instance of NamdKernelScheme2a class
        """

        # ----------------------------------------------------------------------
        #
        def unit_state_change_cb(unit, state):

            if unit:            
                self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )

                if state == rp.states.FAILED:
                    self.logger.error("Log: {0:s}".format( unit.as_dict() ) )
                    # restarting the replica
                    #self.logger.info("ComputeUnit '{0:s}' state changed to {1:s}.".format(unit.uid, state) )
                    #unit_manager.submit_units( unit.description )

        #-----------------------------------------------------------------------
        cycles = md_kernel.nr_cycles + 1
                
        unit_manager = rp.UnitManager(self.session, scheduler=rp.SCHED_DIRECT_SUBMISSION)
        unit_manager.register_callback(unit_state_change_cb)
        unit_manager.add_pilots(self.pilot_object)

        self._prof = rp.utils.Profiler(self.name)
        self._prof.prof('start_run')
        self._prof.prof('stagein_start')

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

        #md_kernel.init_matrices(replicas)

        self._prof.prof('stagein_end')

        start = datetime.datetime.utcnow()
        #-----------------------------------------------------------------------
        # bulk_submission = 0: do sequential submission
        # bulk_submission = 1: do bulk_submission submission
        bulk_submission = 1
        dim_int = 0
        
        dim_count = md_kernel.nr_dims
        dim_str = []
        dim_str.append('')
        for i in range(dim_count):
            s = 'd' + str(i+1)
            dim_str.append(s)

        self._prof.prof('sim_loop_start')
        for c in range(0,cycles*dim_count):

            if dim_int < dim_count:
                dim_int = dim_int + 1
            else:
                dim_int = 1

            current_cycle = c / dim_count

            self.logger.info("Performing cycle: {0}".format(current_cycle) )        
            self.logger.info("Dim {0}: preparing {1} replicas for MD run; cycle {2}".format(dim_int, md_kernel.replicas, current_cycle) )
            
            submitted_groups = []
            exchange_replicas = []
            
            c_str = '_c:' + str(current_cycle) + '_d:' + str(dim_int)
            #-------------------------------------------------------------------
            # sequential submission
            if not bulk_submission:
                pass
            #-------------------------------------------------------------------
            # bulk_submission submision
            else:
                
                self._prof.prof('get_groups_start' + c_str)
                all_groups = md_kernel.get_all_groups(dim_int, replicas)
                self._prof.prof('get_groups_end' + c_str)

                gnr = -1
                c_units = []
                for group in all_groups:
                    gnr += 1

                    self._prof.prof('md_prep_start_g:' + str(gnr) + c_str )
                    compute_group = md_kernel.prepare_group_for_md(dim_int, dim_str[dim_int], group, self.sd_shared_list)
                    c_units.append(compute_group)
                    self._prof.prof('md_prep_end_g:' + str(gnr) + c_str )

                self._prof.prof('md_sub_start_g:' + str(gnr) + c_str )
                submitted_groups += unit_manager.submit_units(c_units)
                self._prof.prof('md_sub_end_g:' + str(gnr) + c_str )

                self._prof.prof('md_wait_start_g:' + str(gnr) + c_str )
                unit_manager.wait_units()
                self._prof.prof('md_wait_end_g:' + str(gnr) + c_str )
                
                #---------------------------------------------------------------
                self._prof.prof('gl_calc_prep_start' + c_str )  
                ex_calculator = md_kernel.prepare_global_ex_calc(current_cycle, dim_int, dim_str[dim_int], replicas, self.sd_shared_list)
                self._prof.prof('gl_calc_prep_end' + c_str )

                self._prof.prof('gl_calc_sub_start' + c_str )
                global_ex_cu = unit_manager.submit_units(ex_calculator)
                self._prof.prof('gl_calc_sub_end' + c_str )

                #---------------------------------------------------------------

                self._prof.prof('gl_calc_wait_start' + c_str )
                unit_manager.wait_units()
                self._prof.prof('gl_calc_wait_end' + c_str )

            #-------------------------------------------------------------------
            #               
            self._prof.prof('local_exchange_start' + c_str )  
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
            md_kernel.do_exchange(current_cycle, dim_int, dim_str[dim_int], replicas)
            self._prof.prof('local_exchange_end' + c_str )   
                
        #-----------------------------------------------------------------------
        # end of loop
        self._prof.prof('end_run')

