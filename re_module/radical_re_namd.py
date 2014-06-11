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
import shutil
from os import path
from kernels.kernels import KERNELS

PWD = os.path.dirname(os.path.abspath(__file__))

#-----------------------------------------------------------------------------------------------------------------------------------

class Replica(object):
    """Class representing replica and it's associated data.
    """
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
#-----------------------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------------------

class RepEx_NamdKernel(object):
    """Class responsible for NAMD related operations. In this class is determined how replica input files
    are composed, how exchanges are performed, etc.
    """
    def __init__(self, inp_file ):
        # NAMD parameters
        try:
            self.namd_path = inp_file['input.NAMD']['namd_path']
        except:
            print "Using default NAMD path for %s" % inp_file['input.PILOT']['resource']
            resource = inp_file['input.PILOT']['resource']
            self.namd_path = KERNELS[resource]["kernels"]["namd"]["executable"]
        self.inp_basename = inp_file['input.NAMD']['input_file_basename']
        self.inp_folder = inp_file['input.NAMD']['input_folder']
        self.namd_structure = inp_file['input.NAMD']['namd_structure']
        self.namd_coordinates = inp_file['input.NAMD']['namd_coordinates']
        self.namd_parameters = inp_file['input.NAMD']['namd_parameters']
        self.replicas = int(inp_file['input.NAMD']['number_of_replicas'])
        self.min_temp = float(inp_file['input.NAMD']['min_temperature'])
        self.max_temp = float(inp_file['input.NAMD']['max_temperature'])
        self.cycle_steps = int(inp_file['input.NAMD']['steps_per_cycle'])
        self.work_dir_local = str(inp_file['input.NAMD']['work_dir_local'])

#----------------------------------------------------------------------------------------------------------------------------------

    def exchange_accept(self, replica, replicas):
        """ This function is using Metropolis criterion to determine of exchange will occur or not. 
        Now if replica already exchanged with some other replica it still can particiate in arbitrary
        number of further exchanges during the same exchange step. 
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
        """Retrieves temperature and potential energy from simulaion output file <file_name>.history
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
        """Builds input file for replica, based on template input file alanin_base.namd
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
            r_file = open( (os.path.join((self.work_dir_local + "/namd_inp/"), template)), "r")
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

        tbuffer = tbuffer.replace("@structure@", self.namd_structure)
        tbuffer = tbuffer.replace("@coordinates@", self.namd_coordinates)
        tbuffer = tbuffer.replace("@parameters@", self.namd_parameters)
        
        replica.cycle += 1
        # write out
        try:
            w_file = open( new_input_file, "w")
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            print 'Warning: unable to access file %s' % new_input_file

#-----------------------------------------------------------------------------------------------------------------------------------

    def prepare_replicas(self, replicas):
        """Prepares all replicas for execuiton. In this function are created CU descriptions for replicas, are
        specified input/output files to be transferred to/from target system. Note: input files for first and 
        subsequent simulaition cycles are different. Currently we only run 1 core replicas.   
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
                structure = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_structure
                coords = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_coordinates
                params = self.work_dir_local + "/" + self.inp_folder + "/" + self.namd_parameters
                cu.input_data = [input_file, structure, coords, params]
                cu.output_data = [new_coor, new_vel, new_history, new_ext_system ]

                compute_replicas.append(cu)
            else:
                cu = radical.pilot.ComputeUnitDescription()
                cu.executable = self.namd_path
                cu.arguments = [input_file]
                cu.cores = 1
                structure = self.inp_folder + "/" + self.namd_structure
                coords = self.inp_folder + "/" + self.namd_coordinates
                params = self.inp_folder + "/" + self.namd_parameters
                cu.input_data = [input_file, structure, coords, params, old_coor, old_vel, old_ext_system]
                cu.output_data = [new_coor, new_vel, new_history, new_ext_system ]
                compute_replicas.append(cu)

        return compute_replicas
            
#-----------------------------------------------------------------------------------------------------------------------------------

    def initialize_replicas(self):
        """Initializes replicas and their attributes to default values
        """
        replicas = []
        for k in range(self.replicas):
            # may consider to change this    
            new_temp = random.uniform(self.max_temp , self.min_temp) * 0.8
            r = Replica(k, new_temp)
            replicas.append(r)
            
        return replicas

#-----------------------------------------------------------------------------------------------------------------------------------

    def move_output_files(self, replicas):
        """Moving files to replica directories
        """
        for r in range(len(replicas)):
            dir_path = "%s/replica_%d" % (self.work_dir_local, r )
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path)
                except: 
                    raise

            files = os.listdir( self.work_dir_local )
            base_name =  self.inp_basename[:-5] + "_%s" % replicas[r].id
            for item in files:
                if item.startswith( base_name ):
                    source =  self.work_dir_local + "/" + str(item)
                    destination = dir_path + "/"
                    shutil.move( source, destination)

#-----------------------------------------------------------------------------------------------------------------------------------

    def clean_up(self, replicas):
        """Delete replica directories
        """
        for r in range(len(replicas)):
            dir_path = "%s/replica_%d" % ( self.work_dir_local, replicas[r].id )
            shutil.rmtree(dir_path)

#-----------------------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------------------            
#-----------------------------------------------------------------------------------------------------------------------------------

class RepEx_PilotKernel(object):
    """This class is using Radical Pilot API to perform all Pilot related operations, such as
    launching a Pilot, running main loop of RE simulation and using RP API for data staging in and out.
    """
    def __init__(self, inp_file, r_config):
        # resource configuration file
        self.rconfig = r_config
        
        # pilot parameters
        self.resource = inp_file['input.PILOT']['resource']
        if self.resource == "localhost.linux.x86":
            self.sandbox = inp_file['input.PILOT']['sandbox']
        else:
            self.sandbox = None
        self.user = inp_file['input.PILOT']['username']
        try:
            self.cores = int(inp_file['input.PILOT']['cores'])
        except:
            self.cores = KERNELS[self.resource]["params"]["cores"]
            print "Using default core count equal %s" %  self.cores
        self.runtime = int(inp_file['input.PILOT']['runtime'])
        try:
            self.dburl = inp_file['input.PILOT']['mongo_url']
        except:
            print "Using default Mongo DB url"
            self.dburl = "mongodb://ec2-184-72-89-141.compute-1.amazonaws.com:27017/"
        self.cleanup = inp_file['input.PILOT']['cleanup']  
        self.nr_cycles = int(inp_file['input.PILOT']['number_of_cycles']) 

#-----------------------------------------------------------------------------------------------------------------------------------

    def run_simulation(self, replicas, session, pilot_object, md_kernel ):
        """This function runs the main loop of RE simulation
        """
        for i in range(self.nr_cycles):
            # returns compute objects
            compute_replicas = md_kernel.prepare_replicas(replicas)
            um = radical.pilot.UnitManager(session=session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
            um.register_callback(self.unit_state_change_cb)
            um.add_pilots(pilot_object)

            submitted_replicas = um.submit_units(compute_replicas)
            um.wait_units()

            for r in replicas:
                # getting OLDTEMP and POTENTIAL from .history file of previous run
                old_temp, old_energy = md_kernel.get_historical_data(r,(r.cycle-1))
                print "************************************************************************"
                print "Replica's %d history data: temperature=%f potential=%f" % ( r.id, old_temp, old_energy )
                print "************************************************************************"
                print ""
                # updating replica temperature
                r.new_temperature = old_temp   
                r.old_temperature = old_temp   
                r.potential = old_energy      

            for r in replicas:
                r_pair = md_kernel.exchange_accept( r, replicas )
                if( r_pair.id != r.id ):
                    # swap temperatures
                    print "************************************************************************"
                    print "Replica %d exchanged temperature with replica %d" % ( r.id, r_pair.id )
                    print "************************************************************************"
                    print ""
                    temperature = r_pair.new_temperature
                    r_pair.new_temperature = r.new_temperature
                    r.new_temperature = temperature
                    # record that swap was performed
                    r.swap = 1
                    r_pair.swap = 1

#-----------------------------------------------------------------------------------------------------------------------------------

    def launch_pilot(self):
        """Launches a Pilot on a target resource. This function uses parameters specified in config/input.json 
        """
        session = None
        pilot_manager = None
        pilot_object = None
   
        try:
            session = radical.pilot.Session(database_url=self.dburl)

            # Add an ssh identity to the session.
            cred = radical.pilot.SSHCredential()
            cred.user_id = self.user
            session.add_credential(cred)

            pilot_manager = radical.pilot.PilotManager(session=session, resource_configurations=self.rconfig)
            pilot_manager.register_callback(self.pilot_state_cb)

            pilot_descripiton = radical.pilot.ComputePilotDescription()
            pilot_descripiton.resource = self.resource
            if self.resource == "localhost.linux.x86":
                pilot_descripiton.sandbox = self.sandbox
            pilot_descripiton.cores = self.cores
            pilot_descripiton.runtime = self.runtime
            pilot_descripiton.cleanup = self.cleanup

            pilot_object = pilot_manager.submit_pilots(pilot_descripiton)

        except radical.pilot.PilotException, ex:
            print "Error: %s" % ex

        return session, pilot_manager, pilot_object 

#-----------------------------------------------------------------------------------------------------------------------------------

    def unit_state_change_cb(self, unit, state):
        """This is a callback function. It gets called very time a ComputeUnit changes its state.
        """
        print "[Callback]: ComputeUnit '{0}' state changed to {1}.".format(
            unit.uid, state)
        if state == radical.pilot.states.FAILED:
            print "            Log: %s" % unit.log[-1]

#-----------------------------------------------------------------------------------------------------------------------------------

    def pilot_state_cb(self, pilot, state):
        """This is a callback function. It gets called very time a ComputePilot changes its state.
        """
        print "[Callback]: ComputePilot '{0}' state changed to {1}.".format(
            pilot.uid, state)

        if state == radical.pilot.states.FAILED:
            sys.exit(1)

#-----------------------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------------------

def parse_command_line():

    usage = "usage: %prog [Options]"
    parser = optparse.OptionParser(usage=usage)

    parser.add_option('--input',
              dest='input_file',
              help='specifies RadicalPilot, NAMD and RE simulation parameters')

    (options, args) = parser.parse_args()

    if options.input_file is None:
        parser.error("You must specify simulation input file (--input). Try --help for help.")

    return options

#-----------------------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------------------
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
    try:
        r_config = inp_file['input.PILOT']['resource_config']
    except:
        print "Using default resource configuration file /config/xsede.json"
        r_config = ('file://localhost%s/' + "/config/xsede.json") % inp_file["input.NAMD"]["work_dir_local"]

    # initializing kernels
    md_kernel = RepEx_NamdKernel( inp_file )
    pilot_kernel = RepEx_PilotKernel( inp_file, r_config )

    # initializing replicas
    replicas = md_kernel.initialize_replicas()
    
    session, pilot_manager, pilot_object = pilot_kernel.launch_pilot()
    
    # now we can run RE simulation
    pilot_kernel.run_simulation( replicas, session, pilot_object, md_kernel )
                
    #session.close()
    
    # finally we are moving all files to individual replica directories
    md_kernel.move_output_files( replicas ) 

    # delete all replica folders
    #md_kernel.clean_up( replicas )

    #sys.exit(0)


