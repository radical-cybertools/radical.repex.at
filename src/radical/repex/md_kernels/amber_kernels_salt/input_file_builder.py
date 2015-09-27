
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
    """
    """

    json_data = sys.argv[1]
    data=json.loads(json_data)

    cycle_steps     = data["cycle_steps"]
    new_salt_concentration = data["new_salt_concentration"]
    amber_input     = data["amber_input"]
    new_input_file  = data["new_input_file"]
    replica_cycle   = int(data["cycle"])

    #---------------------------------------------------------------------------
    # this is for every cycle
    try:
        r_file = open(amber_input, "r")
    except IOError:
        print "Warning: unable to access template file: {0}".format(amber_input) 

    tbuffer = r_file.read()
    r_file.close()

    tbuffer = tbuffer.replace("@nstlim@",cycle_steps)
    #tbuffer = tbuffer.replace("@rstr@",new_restraints)
    #tbuffer = tbuffer.replace("@temp@",new_temperature)
    tbuffer = tbuffer.replace("@salt@",new_salt_concentration)

    try:
        w_file = open(new_input_file, "w")
        w_file.write(tbuffer)
        w_file.close()
    except IOError:
        print "Warning: unable to access file: {0}".format(new_input_file)

    