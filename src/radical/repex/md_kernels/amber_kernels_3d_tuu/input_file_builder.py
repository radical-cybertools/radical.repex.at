
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
    new_restraints  = data["new_restraints"]
    new_temperature = data["new_temperature"]
    amber_input     = data["amber_input"]
    new_input_file  = data["new_input_file"]
    us_template     = data["us_template"]
    replica_cycle   = int(data["cycle"])
    rstr_val_1      = float(data["rstr_val_1"])
    rstr_val_2      = float(data["rstr_val_2"])

    #---------------------------------------------------------------------------
    # this is for every cycle
    try:
        r_file = open(amber_input, "r")
    except IOError:
        print "Warning: unable to access template file: {0}".format(amber_input) 

    tbuffer = r_file.read()
    r_file.close()

    tbuffer = tbuffer.replace("@nstlim@",cycle_steps)
    tbuffer = tbuffer.replace("@disang@",new_restraints)
    tbuffer = tbuffer.replace("@temp@",new_temperature)

    if replica_cycle == 1:
        tbuffer = tbuffer.replace("@irest@","0")
        tbuffer = tbuffer.replace("@ntx@","1")
    else:
        tbuffer = tbuffer.replace("@irest@","1")
        tbuffer = tbuffer.replace("@ntx@","5")

    try:
        w_file = open(new_input_file, "w")
        w_file.write(tbuffer)
        w_file.close()
    except IOError:
        print "Warning: unable to access file: {0}".format(new_input_file)

    #---------------------------------------------------------------------------
    # this is for first cycle only
    if replica_cycle == 1:
        print "first cycle"
        try:
            r_file = open(us_template, "r")
            tbuffer = r_file.read()
            r_file.close()
        except IOError:
            print "Warning: unable to access file: {0}".format(us_template) 

        try:
            w_file = open(new_restraints, "w")
            tbuffer = tbuffer.replace("@val1@", str(rstr_val_1))
            tbuffer = tbuffer.replace("@val1l@", str(rstr_val_1-90))
            tbuffer = tbuffer.replace("@val1h@", str(rstr_val_1+90))
            tbuffer = tbuffer.replace("@val2@", str(rstr_val_2))
            tbuffer = tbuffer.replace("@val2l@", str(rstr_val_2-90))
            tbuffer = tbuffer.replace("@val2h@", str(rstr_val_2+90))
            w_file.write(tbuffer)
            w_file.close()
        except IOError:
            print "Warning: unable to access file: {0}".format(new_restraints)
 
        #-----------------------------------------------------------------------
        # copy to staging area
        pwd = os.getcwd()
        src = pwd + "/" + new_restraints

        size = len(pwd)-1
        path = pwd
        for i in range(0,size):
            if pwd[size-i] != '/':
                path = path[:-1]
            else:
                break

        dst = path + "staging_area/" + new_restraints 
        shutil.copyfile(src, dst)

