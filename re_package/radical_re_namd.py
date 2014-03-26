import os
import sys
import time
import math
import json
import optparse
import datetime
#import sagapilot
from pprint import pprint

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
        self.old_temperature = new_temperature

#-----------------------------------------------------------------------------------------------------------------------------------

class ReplicaExchange(object):

    def __init__(self, inp_file, r_config ):
        # resource configuration file
        self.rconfig = r_config

        # pilot parameters
        self.resource = inp_file['input.PILOT']['resource']
        self.sandbox = inp_file['input.PILOT']['sandbox']
        self.cores = inp_file['input.PILOT']['cores']
        self.runtime = inp_file['input.PILOT']['runtime']
        self.dburl = inp_file['input.PILOT']['mongo_url']
        self.cleanup = inp_file['input.PILOT']['cleanup']

        # NAMD parameters
        self.namd_path = inp_file['input.NAMD']['namd_path']
        self.inp_basename = inp_file['input.NAMD']['input_file_basename']
        self.replicas = inp_file['input.NAMD']['number_of_replicas']
        self.min_temp = inp_file['input.NAMD']['min_temperature']
        self.max_temp = inp_file['input.NAMD']['max_temperature']
        self.timestep = inp_file['input.NAMD']['timestep']
        self.cycle_steps = inp_file['input.NAMD']['steps_per_cycle']

#-----------------------------------------------------------------------------------------------------------------------------------

    def _parseInputFile(self):
        """ 
        Check that required parameters are specified.
        """ 
        # Required Options
        #############################
        # pilot parameters
        if self.resource is None:
            sys.exit('Resource name (resource) is not specified in input.PILOT!')
        elif self.sandbox is None:
            sys.exit('Working directory (sandbox) is not specified in input.PILOT!')
        elif self.cores is None:
            sys.exit('Number of cores (cores) is not specified in input.PILOT!')
        elif self.runtime is None:
            sys.exit('Total simulation runtime (runtime) is not specified in input.PILOT!')
        elif self.mongo_url is None:
            sys.exit('Mongo DB url (mongo_url) is not specified in input.PILOT!')    
        elif self.cleanup is None:
            sys.exit('cleanup is not specified in input.PILOT!') 

        # namd parameters
        if self.namd_path is None:
            sys.exit('Path to NAMD executable (namd_path) is not specified in input.NAMD!')
        elif self.inp_basename is None:
            sys.exit('Base name for NAMD simulation input file (input_file_basename) is not specified in input.NAMD!')
        elif self.replicas is None:
            sys.exit('Number of replicas for NAMD simulation (number_of_replicas) is not specified in input.NAMD!')
        elif self.min_temp is None:
            sys.exit('NAMD simulation minimum temperature (min_temperature) is not specified in input.NAMD!')
        elif self.max_temp is None:
            sys.exit('NAMD simulation maximum temperature (max_temperature) is not specified in input.NAMD!')
        elif self.timestep is None:
            sys.exit('NAMD simulation (timestep) is not specified in input.NAMD!')
        elif self.cycle_steps is None:
            sys.exit('Steps per NAMD simulation cycle (steps_per_cycle) is not specified in input.NAMD!')

#-----------------------------------------------------------------------------------------------------------------------------------

    def buildInputFiles(self, replica_nr):
        """BROKEN!
        """

        # cycle_current starts with 1

        # this is 
        stateid = self.status[replica]['stateid_current']
        cycle = self.status[replica]['cycle_current']
        namd_run = cycle - 1

        #
        template = self.inp_basename

        inpfile = "r%d/%s_%d.namd" % (replica, basename, cycle)
        #outputname = "r%d_%s_%d" % (replica, basename, cycle)
        outputname = "%s_%d_output" % (basename, cycle)
        old_name = "%s_%d_output" % (basename, namd_run)
        historyname = "%s_%d.history" % (basename, cycle)
        #cycle_output_file = "r%d/h_%s_%d.history" % (replica, self.basename, cycle)  

        # ok
        my_newtemp = self.stateparams[stateid]['newtemp']

        # getting OLDTEMP from .history file of previous run
        if cycle == 1:
            my_oldtemp = my_newtemp
        else:
            #old_data = self._getTempPot(replica,(cycle-1))
            #my_oldtemp = old_data[0]
            output = "r%d/%s_%d.history" % (replica, basename, (cycle-1))
            my_oldtemp = self._getNamdTemperature(output)

        #print "I AM REPLICA: %d MY NEWTEMP IS: %d MY OLDTEMP IS: %d" % (replica, my_newtemp, my_oldtemp)

        if abs(my_newtemp-my_oldtemp) > 1.0:
            swap = 1
            #print "EXCHANGE ACCEPTED FOR REPLICA %d" % replica
        else:
            swap = 0

        #print "I AM REPLICA: %d MY STATE ID IS: %d" % (replica, stateid)

        my_steps_per_cycle = self.steps_per_cycle
        my_timestep = self.timestep

        if (cycle == 1):
            first_step = 0
        else:
            first_step = (cycle - 1) * int(my_steps_per_cycle)


        # read template buffer
        tfile = self._openfile(template, "r")
        tbuffer = tfile.read()
        tfile.close()

        tbuffer = tbuffer.replace("@swap@",str(swap))
        tbuffer = tbuffer.replace("@ot@",str(my_oldtemp))
        tbuffer = tbuffer.replace("@nt@",str(my_newtemp))
        tbuffer = tbuffer.replace("@pr@",str(my_steps_per_cycle))
        # steps per run; keeping option to provide separate values for steps_per_run and stepspercycle
        tbuffer = tbuffer.replace("@steps@",str(my_steps_per_cycle))
        tbuffer = tbuffer.replace("@rid@",str(replica))
        tbuffer = tbuffer.replace("@stp@",str(my_timestep))
        tbuffer = tbuffer.replace("@somename@",str(outputname))
        tbuffer = tbuffer.replace("@oldname@",str(old_name))
        tbuffer = tbuffer.replace("@cycle@",str(namd_run))
        tbuffer = tbuffer.replace("@firststep@",str(first_step))
        tbuffer = tbuffer.replace("@history@",str(historyname))
        
        # write out
        ofile = self._openfile(inpfile, "w")
        ofile.write(tbuffer)
        ofile.close()


#-----------------------------------------------------------------------------------------------------------------------------------

    def launch(self,replica,cycle):
         """BROKEN!
         """

         basefile = ''

         # each replica has it's own input file - simulation_name.namd
         # through this file all input parameters and other input files are provided
         input_file = "%s_%d.namd" % (self.basename, cycle)

         #-------------------------------------------------------------
         cu = sagapilot.ComputeUnitDescription()
         cu.cores = 1
         cu.executable = NAMD_PATH
         cu.arguments  = input_file
         #-------------------------------------------------------------

#-----------------------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------------------
#-----------------------------------------------------------------------------------------------------------------------------------

def parseCommandLine():

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

    params = parseCommandLine()
    
    # get input file
    json_data=open(params.input_file)
    inp_file = json.load(json_data)
    json_data.close()

    # get resource
    r_config = ('file://localhost/%s/' + str(params.resource_file)) % PWD

    r = ReplicaExchange( inp_file, r_config )

    print ""
    print "******************************"
    print "* Replica Exchange with NAMD *"
    print "******************************"
    print ""

