import os
import sys
import json
import os.path
import optparse
import radical.pilot
from kernels.kernels import KERNELS
from pilot_kernels.pilot_kernel_s2 import PilotKernelS2
from launch_simulation_s2 import parse_command_line
from radical.ensemblemd.mdkernels import MDTaskDescription

#---------------------------------------------------------------------------------------------


if __name__ == '__main__':

    params = parse_command_line()
    
    # get input file
    json_data=open(params.input_file)
    inp_file = json.load(json_data)
    json_data.close()

    resource = inp_file['input.PILOT']['resource']
    username = inp_file['input.PILOT']['username']

    mdtd = MDTaskDescription()
    mdtd.kernel = "NAMD"
    mdtd.arguments = "--version"    

    mdtd_bound = mdtd.bind(resource=resource)

    task_desc = radical.pilot.ComputeUnitDescription()
    task_desc.environment = mdtd_bound.environment 
    task_desc.pre_exec    = mdtd_bound.pre_exec
    task_desc.executable  = mdtd_bound.executable
    task_desc.arguments   = mdtd_bound.arguments
    task_desc.cores       = inp_file['input.NAMD']['replica_cores']
    task_desc.mpi         = False

    session = None
    pilot_manager = None
    pilot_object = None

    try:
        dburl = "mongodb://ec2-184-72-89-141.compute-1.amazonaws.com:27017/"
        session = radical.pilot.Session(database_url=dburl)

        # Add an ssh identity to the session.
        cred = radical.pilot.SSHCredential()
        cred.user_id = username
        session.add_credential(cred)

        pilot_manager = radical.pilot.PilotManager(session=session)
        pilot_manager.register_callback(PilotKernelS2.pilot_state_cb)

        #-----------------------------------------------------------
        pilot_descripiton = radical.pilot.ComputePilotDescription()
        pilot_descripiton.resource = resource
        pilot_descripiton.cores = KERNELS[resource]["params"]["cores"]
        pilot_descripiton.runtime = inp_file["input.PILOT"]["runtime"]
        pilot_descripiton.cleanup = inp_file["input.PILOT"]["cleanup"]
        #-----------------------------------------------------------

        pilot_object = pilot_manager.submit_pilots(pilot_descripiton)

        um = radical.pilot.UnitManager(session=session, scheduler=radical.pilot.SCHED_ROUND_ROBIN)
        um.register_callback(PilotKernelS2.unit_state_change_cb)
        um.add_pilots(pilot_object)

        submitted_units = um.submit_units(task_desc)
        um.wait_units()

    except radical.pilot.PilotException, ex:
        print "Error: %s" % ex



