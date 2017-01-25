"""
.. module:: radical.repex.remote_application_modules.ram_namd.input_file_builder
.. moduleauthor::  <antons.treikalis@gmail.com>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import json
import math
import time
import shutil

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    """Uses .namd template to prepare an input file for this replica (before 
    every MD simulation).
    """

    json_data = sys.argv[1]
    data=json.loads(json_data)

    inp_basename = data["inp_basename"]
    replica_id = int(data["replica_id"])
    replica_cycle = int(data["replica_cycle"])
    cycle_steps = int(data["cycle_steps"])
    namd_structure = (data["namd_structure"])
    namd_coordinates = (data["namd_coordinates"])
    namd_parameters = (data["namd_parameters"])
    swap = (data["swap"])
    old_temperature = (data["old_temperature"])
    new_temperature = (data["new_temperature"])

    #---------------------------------------------------------------------------

    basename = inp_basename
    template = inp_basename + ".namd"
        
    new_input_file = "%s_%d_%d.namd" % (basename, replica_id, replica_cycle)
    outputname = "%s_%d_%d" % (basename, replica_id, replica_cycle)
    old_name = "%s_%d_%d" % (basename, replica_id, (replica_cycle-1))
    historyname = outputname + ".history"

    if (replica_cycle == 0):
        first_step = 0
    elif (replica_cycle == 1):
        first_step = int(cycle_steps)
    else:
        first_step = (replica_cycle - 1) * int(cycle_steps)

    if (replica_cycle == 0): 
        structure = namd_structure
        coordinates = namd_coordinates
        parameters = namd_parameters
    else:
        structure   = namd_structure
        coordinates = namd_coordinates
        parameters  = namd_parameters

    old_path = "../staging_area/" + old_name

    # substituting tokens in main replica input file 
    try:
        r_file = open(template, "r")
    except IOError:
        print "Warning: unable to access template file: {0}".format(template) 

    tbuffer = r_file.read()
    r_file.close()

    tbuffer = tbuffer.replace("@swap@",str(swap))
    tbuffer = tbuffer.replace("@ot@",str(old_temperature))
    tbuffer = tbuffer.replace("@nt@",str(new_temperature))
    tbuffer = tbuffer.replace("@steps@",str(cycle_steps))
    tbuffer = tbuffer.replace("@rid@",str(replica_id))
    tbuffer = tbuffer.replace("@somename@",str(outputname))
    tbuffer = tbuffer.replace("@oldname@",str(old_path))
    tbuffer = tbuffer.replace("@cycle@",str(replica_cycle))
    tbuffer = tbuffer.replace("@firststep@",str(first_step))
    tbuffer = tbuffer.replace("@history@",str(historyname))
    tbuffer = tbuffer.replace("@structure@", str(structure))
    tbuffer = tbuffer.replace("@coordinates@", str(coordinates))
    tbuffer = tbuffer.replace("@parameters@", str(parameters))
    
    # write out
    try:
        w_file = open(new_input_file, "w")
        w_file.write(tbuffer)
        w_file.close()
    except IOError:
        print "Warning: unable to access file: {0}".format(new_input_file)

