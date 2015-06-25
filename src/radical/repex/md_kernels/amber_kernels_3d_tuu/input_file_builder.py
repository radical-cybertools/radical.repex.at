
__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys

#--------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    """
    """

    
    argument_list   = str(sys.argv)
    cycle_steps     = str(sys.argv[1])
    new_restraints  = str(sys.argv[2])
    new_temperature = str(sys.argv[3])
    amber_input     = str(sys.argv[4])
    new_input_file  = str(sys.argv[5])
    us_template     = str(sys.argv[6])
    replica_cycle   = int(sys.argv[7])
    rstr_val_1      = float(sys.argv[8])
    rstr_val_2      = float(sys.argv[9])

    print "replica cycle: %d" % replica_cycle
    print "us template: %s" % us_template
    print "new_input_file: %s" % new_input_file
    print "amber_input: %s" % amber_input
    #-------------------------------------------------------------------------
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

    try:
        w_file = open(new_input_file, "w")
        w_file.write(tbuffer)
        w_file.close()
    except IOError:
        print "Warning: unable to access file: {0}".format(new_input_file)

    #-------------------------------------------------------------------------
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

