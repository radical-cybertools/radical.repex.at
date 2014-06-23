import os
import sys
import time
import radical.pilot

DBURL = os.getenv("RADICAL_PILOT_DBURL")
if DBURL is None:
    print "ERROR: RADICAL_PILOT_DBURL (MongoDB server URL) is not defined."
    sys.exit(1)

#------------------------------------------------------------------------------
#
def pilot_state_cb(pilot, state):
    """pilot_state_change_cb() is a callback function. It gets called very
    time a ComputePilot changes its state.
    """
    print "[Callback]: ComputePilot '{0}' state changed to {1}.".format(
        pilot.uid, state)

    if state == radical.pilot.states.FAILED:
        sys.exit(1)

#------------------------------------------------------------------------------
#
def unit_state_change_cb(unit, state):
    """unit_state_change_cb() is a callback function. It gets called very
    time a ComputeUnit changes its state.
    """
    print "[Callback]: ComputeUnit '{0}' state changed to {1}.".format(
        unit.uid, state)
    if state == radical.pilot.states.FAILED:
        print "            Log: %s" % unit.log[-1]

#------------------------------------------------------------------------------
#
if __name__ == "__main__":

    try:
        session = radical.pilot.Session(database_url=DBURL)
 
        cred = radical.pilot.SSHCredential()
        cred.user_id = "antontre"
        session.add_credential(cred)

        pmgr = radical.pilot.PilotManager(session=session)
        pmgr.register_callback(pilot_state_cb)

        pdesc = radical.pilot.ComputePilotDescription()
        pdesc.resource = "trestles.sdsc.xsede.org"
        pdesc.runtime  = 5 
        pdesc.cores    = 32
        pdesc.cleanup  = False

        pilot = pmgr.submit_pilots(pdesc)

        md_compute_units = []
        for unit_count in range(0, 32):
            cu = radical.pilot.ComputeUnitDescription()
            cu.executable  = "/bin/date"
            cu.output_data  = ["STDOUT"]
            cu.cores       = 1
            md_compute_units.append(cu)

        ex_compute_units = []
        for unit_count in range(0, 32):
            cu = radical.pilot.ComputeUnitDescription()
            cu.executable  = "/bin/hostname"
            cu.output_data  = ["STDOUT"]
            cu.cores       = 1
            ex_compute_units.append(cu)

        md_unit_manager = radical.pilot.UnitManager(session=session, scheduler=radical.pilot.SCHED_DIRECT_SUBMISSION)
        md_unit_manager.register_callback(unit_state_change_cb)
        md_unit_manager.add_pilots(pilot)

        ex_unit_manager = radical.pilot.UnitManager(session=session, scheduler=radical.pilot.SCHED_DIRECT_SUBMISSION)
        ex_unit_manager.register_callback(unit_state_change_cb)
        ex_unit_manager.add_pilots(pilot)
      
        for i in range(0,2):
            md_units = md_unit_manager.submit_units(md_compute_units)
            md_unit_manager.wait_units()

            ############################
            # do something here...     #
            ############################
  
            ex_units = ex_unit_manager.submit_units(ex_compute_units)
            ex_unit_manager.wait_units()

        session.close()
        sys.exit(0)

    except radical.pilot.PilotException, ex:
        print "Error during execution: %s" % ex
        sys.exit(1)
