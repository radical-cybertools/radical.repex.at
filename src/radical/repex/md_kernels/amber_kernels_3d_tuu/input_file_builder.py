
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

