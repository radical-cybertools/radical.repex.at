import os
import sys
import json
import os.path
import optparse
import radical.pilot
from kernels.kernels import KERNELS
from radical.ensemblemd.mdkernels import MDTaskDescription
from re_module.radical_re_namd import Replica as Replica
from re_module.radical_re_namd import RepEx_NamdKernel as namdKernel
from re_module.radical_re_namd import RepEx_PilotKernel as pilotKernel

#---------------------------------------------------------------------------------------------

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


def unit_state_change_cb(self, unit, state):
    """This is a callback function. It gets called very time a ComputeUnit changes its state.
    """
    print "[Callback]: ComputeUnit '{0}' state changed to {1}.".format(unit.uid, state)
    if state == radical.pilot.states.FAILED:
        print "Log: %s" % unit.log[-1]


def pilot_state_cb(self, pilot, state):
    """This is a callback function. It gets called very time a ComputePilot changes its state.
    """
    print "[Callback]: ComputePilot '{0}' state changed to {1}.".format(pilot.uid, state)
    if state == radical.pilot.states.FAILED:
        sys.exit(1)


if __name__ == '__main__':

    params = parse_command_line()
    
    # get input file
    json_data=open(params.input_file)
    inp_file = json.load(json_data)
    json_data.close()

    try:
        r_config = inp_file['input.PILOT']['resource_config']
    except:
        print "Using default resource configuration file /config/xsede.json"
        r_config = ('file://localhost%s/' + "/config/xsede.json") % inp_file["input.NAMD"]["work_dir_local"]

    mdtd = MDTaskDescription()
    mdtd.kernel = "NAMD"
    mdtd.arguments = "--version"    

    resource_r = inp_file["input.PILOT"]["resource"]
    cores_c = KERNELS[resource_r]["params"]["cores"]
    mdtd_bound = mdtd.bind(resource=resource_r, cores=cores_c)

    task_desc = radical.pilot.ComputeUnitDescription()
    task_desc.environment = mdtd_bound.environment 
    task_desc.pre_exec    = mdtd_bound.pre_exec
    task_desc.executable  = mdtd_bound.executable
    task_desc.arguments   = mdtd_bound.arguments
    task_desc.cores       = 2

    session = None
    pilot_manager = None
    pilot_object = None

    try:
        dburl = "mongodb://ec2-184-72-89-141.compute-1.amazonaws.com:27017/"
        session = radical.pilot.Session(database_url=dburl)

        # Add an ssh identity to the session.
        cred = radical.pilot.SSHCredential()
        cred.user_id = inp_file["input.PILOT"]["username"]
        session.add_credential(cred)

        pilot_manager = radical.pilot.PilotManager(session=session)
        pilot_manager.register_callback(pilot_state_cb)

        #-----------------------------------------------------------
        pilot_descripiton = radical.pilot.ComputePilotDescription()
        pilot_descripiton.resource = inp_file["input.PILOT"]["resource"]
        pilot_descripiton.cores = cores_c
        pilot_descripiton.runtime = inp_file["input.PILOT"]["runtime"]
        pilot_descripiton.cleanup = inp_file["input.PILOT"]["clenaup"]
        #-----------------------------------------------------------

        pilot_object = pilot_manager.submit_pilots(pilot_descripiton)


        um = radical.pilot.UnitManager(session=session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        um.register_callback(unit_state_change_cb)
        um.add_pilots(pilot_object)

        submitted_units = um.submit_units(task_desc)
        um.wait_units()

    except radical.pilot.PilotException, ex:
        print "Error: %s" % ex



