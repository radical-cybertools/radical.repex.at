#!/usr/bin/python2.7

import os
import sys
import time
import math
import json
import optparse
import datetime
import radical.pilot
from pprint import pprint
from random import randint
import random

PWD = os.path.dirname(os.path.abspath(__file__))

#-----------------------------------------------------------------------------------------------------------------------------------

class Replica(object):

    def __init__(self, my_id, new_temperature = None):
        self.id = my_id
        self.partner = -1
        self.state = 'initialized'
        self.cycle = 0
        if new_temperature is None:
            self.new_temperature = 0
        else:
            self.new_temperature = new_temperature
        self.old_temperature = new_temperature
        self.potential = 0 
        self.new_coor = ""
        self.new_vel = ""
        self.new_history = ""
        self.new_ext_system = "" 
        self.old_coor = ""
        self.old_vel = ""
        self.old_ext_system = "" 
        self.swap = 0

#-----------------------------------------------------------------------------------------------------------------------------------

class ReplicaExchange(object):

    def __init__(self, inp_file, r_config ):
        # resource configuration file
        self.rconfig = r_config
        
        # pilot parameters
        self.resource = inp_file['input.PILOT']['resource']
        self.sandbox = inp_file['input.PILOT']['sandbox']
        self.cores = int(inp_file['input.PILOT']['cores'])
        self.runtime = int(inp_file['input.PILOT']['runtime'])
        self.dburl = inp_file['input.PILOT']['mongo_url']
        self.cleanup = inp_file['input.PILOT']['cleanup']

        # NAMD parameters
        self.namd_path = inp_file['input.NAMD']['namd_path']
        self.inp_basename = inp_file['input.NAMD']['input_file_basename']
        self.namd_structure = inp_file['input.NAMD']['namd_structure']
        self.namd_coordinates = inp_file['input.NAMD']['namd_coordinates']
        self.namd_parameters = inp_file['input.NAMD']['namd_parameters']
        self.replicas = int(inp_file['input.NAMD']['number_of_replicas'])
        self.min_temp = float(inp_file['input.NAMD']['min_temperature'])
        self.max_temp = float(inp_file['input.NAMD']['max_temperature'])
        self.cycle_steps = int(inp_file['input.NAMD']['steps_per_cycle'])
        self.nr_cycles = int(inp_file['input.NAMD']['number_of_cycles'])

        # check if all required params are specified
        self.check_parameters()

#-----------------------------------------------------------------------------------------------------------------------------------

    def check_parameters(self):
        """ 
        Check that required parameters are specified.
        """ 

        for attribute, value in self.__dict__.iteritems():
            if value is None:
                sys.exit('Parameter %s is not specified in input.json!' % attribute)

#----------------------------------------------------------------------------------------------------------------------------------

    def exchange_accept(self, replica, replicas):
        """ This function is using Metropolis criterion to determine of exchange will occur or not. 
        Now if replica already exchanged with some other replica it still can particiate in arbitrary
        number of further exchanges during the same exchange step. Is this correct behaviour? 
        """
        kb = 0.0019872041

        for partner in replicas:            
            dbeta = ((1./replica.new_temperature) - (1./partner.new_temperature)) / kb
            delta = dbeta * (partner.potential - replica.potential)
            swp = ( delta < 0. ) or (( -1. * delta ) > random.random())
            if swp:
                return partner
                
        #if no exchange is found then return replica
        return replica

#----------------------------------------------------------------------------------------------------------------------------------

    def get_historical_data(self, replica, cycle):
        """
        """
        if not os.path.exists(replica.new_history):
            print "history file not found: "
            print replica.new_history
        else:
            f = open(replica.new_history)
            lines = f.readlines()
            f.close()
            data = lines[0].split()
         
        return float(data[0]), float(data[1])

#----------------------------------------------------------------------------------------------------------------------------------

    def build_input_file(self, replica):
        """
        Builds input file for replica, based on template input file alanin_base.namd
        """

        basename = self.inp_basename[:-5]
        template = self.inp_basename
            
        new_input_file = "%s_%d_%d.namd" % (basename, replica.id, replica.cycle)
        outputname = "%s_%d_%d_out" % (basename, replica.id, replica.cycle)
        old_name = "%s_%d_%d_out" % (basename, replica.id, (replica.cycle-1))
        replica.new_coor = outputname + ".coor"
        replica.new_vel = outputname + ".vel"
        replica.new_history = outputname + ".history"
        replica.new_ext_system = outputname + ".xsc" 

        historyname = replica.new_history

        replica.old_coor = old_name + ".coor"
        replica.old_vel = old_name + ".vel"
        replica.old_ext_system = old_name + ".xsc" 

        if (replica.cycle == 0):
            first_step = 0
        elif (replica.cycle == 1):
            first_step = int(self.cycle_steps)
        else:
            first_step = (replica.cycle - 1) * int(self.cycle_steps)

        #---------------------------------------------------------------------
        # substituting tokens in main replica input file 
        try:
            r_file = open(template, "r")
        except IOError:
            print 'Warning: unable to access template file %s' % template

        tbuffer = r_file.read()
        r_file.close()

        tbuffer = tbuffer.replace("@swap@",str(replica.swap))
        tbuffer = tbuffer.replace("@ot@",str(replica.old_temperature))
        tbuffer = tbuffer.replace("@nt@",str(replica.new_temperature))
        tbuffer = tbuffer.replace("@steps@",str(self.cycle_steps))
        tbuffer = tbuffer.replace("@rid@",str(replica.id))
        tbuffer = tbuffer.replace("@somename@",str(outputname))
        tbuffer = tbuffer.replace("@oldname@",str(old_name))
        tbuffer = tbuffer.replace("@cycle@",str(replica.cycle))
        tbuffer = tbuffer.replace("@firststep@",str(first_step))
        tbuffer = tbuffer.replace("@history@",str(historyname))
        
        replica.cycle += 1
        # write out
        try:
            w_file = open(new_input_file, "w")
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            print 'Warning: unable to access file %s' % new_input_file

#-----------------------------------------------------------------------------------------------------------------------------------

    def prepare_replicas(self, replicas):
        """
        """
        compute_replicas = []
        for r in range(len(replicas)):
            self.build_input_file(replicas[r])
            input_file = "%s_%d_%d.namd" % (self.inp_basename[:-5], replicas[r].id, (replicas[r].cycle-1))

            new_coor = replicas[r].new_coor
            new_vel = replicas[r].new_vel
            new_history = replicas[r].new_history
            new_ext_system = replicas[r].new_ext_system

            old_coor = replicas[r].old_coor
            old_vel = replicas[r].old_vel
            old_ext_system = replicas[r].old_ext_system 

            if replicas[r].cycle == 1:
                cu = radical.pilot.ComputeUnitDescription()
                cu.executable = self.namd_path
                cu.arguments = [input_file]
                cu.cores = 1
                cu.input_data = [input_file, self.namd_structure, self.namd_coordinates, self.namd_parameters]
                cu.output_data = [new_coor, new_vel, new_history, new_ext_system ]

                compute_replicas.append(cu)
            else:
                cu = radical.pilot.ComputeUnitDescription()
                cu.executable = self.namd_path
                cu.arguments = [input_file]
                cu.cores = 1
                cu.input_data = [input_file, self.namd_structure, self.namd_coordinates, self.namd_parameters, old_coor, old_vel, old_ext_system]
                cu.output_data = [new_coor, new_vel, new_history, new_ext_system ]
                compute_replicas.append(cu)

        return compute_replicas
            
#-----------------------------------------------------------------------------------------------------------------------------------

    def unit_state_change_cb(self, unit, state):
        """unit_state_change_cb() is a callback function. It gets called very
        time a ComputeUnit changes its state.
        """
        print "[Callback]: ComputeUnit '{0}' state changed to {1}.".format(
            unit.uid, state)
        if state == radical.pilot.states.FAILED:
            print "            Log: %s" % unit.log[-1]

#-----------------------------------------------------------------------------------------------------------------------------------

    def pilot_state_cb(self, pilot, state):
        """pilot_state_change_cb() is a callback function. It gets called very
        time a ComputePilot changes its state.
        """
        print "[Callback]: ComputePilot '{0}' state changed to {1}.".format(
            pilot.uid, state)

        if state == radical.pilot.states.FAILED:
            sys.exit(1)

#-----------------------------------------------------------------------------------------------------------------------------------

    def launch_pilot(self, r_config):
        
        session = None
        pilot_manager = None
        pilot_object = None
   
        try:
            session = radical.pilot.Session(database_url=self.dburl)

            pilot_manager = radical.pilot.PilotManager(session=session, resource_configurations=r_config)
            pilot_manager.register_callback(self.pilot_state_cb)

            pilot_descripiton = radical.pilot.ComputePilotDescription()
            pilot_descripiton.resource = self.resource
            pilot_descripiton.sandbox = self.sandbox
            pilot_descripiton.cores = self.cores
            pilot_descripiton.runtime = self.runtime
            pilot_descripiton.cleanup = self.cleanup

            pilot_object = pilot_manager.submit_pilots(pilot_descripiton)

        except radical.pilot.PilotException, ex:
            print "Error: %s" % ex

        return session, pilot_manager, pilot_object 

#-----------------------------------------------------------------------------------------------------------------------------------

    def initialize_replicas(self):

        replicas = []
        for k in range(self.replicas):
            # may consider to change this    
            new_temp = random.uniform(self.max_temp , self.min_temp) * 0.8
            r = Replica(k, new_temp)
            replicas.append(r)
            
        return replicas

#-----------------------------------------------------------------------------------------------------------------------------------

def parse_command_line():

    usage = "usage: %prog [Options]"
    parser = optparse.OptionParser(usage=usage)

    parser.add_option('--input',
              dest='input_file',
              help='specifies RadicalPilot, NAMD and RE simulation parameters')

    parser.add_option('--resource',
              dest='resource_file',
              help='specifies configuration parameters of the resource, RE simulaiton is intended to be run on')

    (options, args) = parser.parse_args()

    if options.input_file is None:
        parser.error("You must specify simulation input file (--input). Try --help for help.")
    elif options.resource_file is None:
        parser.error("You must specify a resource file (--resource). Try --help for help.")

    return options

#-----------------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':

    print "*********************************************************************"
    print "*                     Replica Exchange with NAMD                    *"
    print "*********************************************************************"

    params = parse_command_line()
    
    # get input file
    json_data=open(params.input_file)
    inp_file = json.load(json_data)
    json_data.close()

    # get resource
    r_config = ('file://localhost%s/' + str(params.resource_file)) % PWD

    # init simulaiton
    re = ReplicaExchange( inp_file, r_config )

    # init replicas
    replicas = re.initialize_replicas()
    session, pilot_manager, pilot_object = re.launch_pilot(r_config)

    for i in range(re.nr_cycles):
        # returns compute objects
        compute_replicas = re.prepare_replicas(replicas)
        um = radical.pilot.UnitManager(session=session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        um.register_callback(re.unit_state_change_cb)
        um.add_pilots(pilot_object)

        submitted_replicas = um.submit_units(compute_replicas)
        um.wait_units()

        for r in replicas:
            # getting OLDTEMP and POTENTIAL from .history file of previous run
            old_temp, old_energy = re.get_historical_data(r,(r.cycle-1))
            print "*********************************************************************"
            print "Replica's %d history data: temperature=%f potential=%f" % ( r.id, old_temp, old_energy )
            print "*********************************************************************"
            print ""
            # updating replica temperature
            r.new_temperature = old_temp   
            r.old_temperature = old_temp   
            r.potential = old_energy      

        for r in replicas:
            r_pair = re.exchange_accept( r, replicas )
            if( r_pair.id != r.id ):
                # swap temperatures
                print "*********************************************************************"
                print "Replica %d exchanged temperature with replica %d" % ( r.id, r_pair.id )
                print "*********************************************************************"
                print ""
                temperature = r_pair.new_temperature
                r_pair.new_temperature = r.new_temperature
                r.new_temperature = temperature
                # record that swap was performed
                r.swap = 1
                r_pair.swap = 1
                
    session.close()
    sys.exit(0)


