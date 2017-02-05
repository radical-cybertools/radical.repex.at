"""
.. module:: radical.repex.remote_application_modules.ram_amber.input_file_builder
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
    """Uses .mdin template to prepare an input file for this replica (before 
    every MD simulation).
    Uses .RST template to prepare .RST file for this replica (befor first 
    MD simulation, later we reuse prepared file) if we are performing umbrella 
    exchange or running multi-dimensional RE with one or more dimensions 
    performing umbrella exchange.
    """

    json_data = sys.argv[1]
    data=json.loads(json_data)

    cycle_steps     = data["cycle_steps"]
    new_restraints  = data["new_restraints"]
    amber_input     = data["amber_input"]
    new_input_file  = data["new_input_file"]
    us_template     = data["us_template"]
    replica_cycle   = int(data["cycle"])
    nr_dims         = int(data["nr_dims"])
    init_temp       = float(data["init_temp"])

    if nr_dims == 3:
        dim_str = ['1', '2', '3']
    elif nr_dims == 2:
        dim_str = ['1', '2']
    elif nr_dims == 1:
        dim_str = ['1']

    dims = []
    for d in dim_str:
        par = float(data[('p'+d)])
        typ = data[('t'+d)]
        dims.append( [typ, par] )

    umbrellas = 0
    new_temperature = None

    new_salt = None
    for pair in dims:
        if pair[0] == 'temperature':
            new_temperature = pair[1]
        if pair[0] == 'salt':
            new_salt = pair[1]
        if pair[0] == 'umbrella':
            umbrellas += 1
            if umbrellas == 1:
                rstr_val_1 = pair[1]
            if umbrellas == 2:
                rstr_val_2 = pair[1]
                    
    if new_temperature is None:
        new_temperature = init_temp
    #---------------------------------------------------------------------------
    # this is for every cycle
    try:
        r_file = open(amber_input, "r")
    except IOError:
        print "Warning: unable to access template file: {0}".format(amber_input) 

    tbuffer = r_file.read()
    r_file.close()

    if (umbrellas > 0):
        tbuffer = tbuffer.replace("@disang@",new_restraints)

    tbuffer = tbuffer.replace("@nstlim@",cycle_steps)
    tbuffer = tbuffer.replace("@temp@", str(new_temperature))

    if replica_cycle == 1:
        tbuffer = tbuffer.replace("@irest@","0")
        tbuffer = tbuffer.replace("@ntx@","1")
    else:
        tbuffer = tbuffer.replace("@irest@","1")
        tbuffer = tbuffer.replace("@ntx@","5")
    if new_salt is not None:
        tbuffer = tbuffer.replace("@salt@",str(new_salt) )
    try:
        w_file = open(new_input_file, "w")
        w_file.write(tbuffer)
        w_file.close()
    except IOError:
        print "Warning: unable to access file: {0}".format(new_input_file)

    #---------------------------------------------------------------------------
    # this is for first cycle only, if we have umbrella dimension
    if (replica_cycle == 1) and (umbrellas > 0):
        try:
            r_file = open(us_template, "r")
            tbuffer = r_file.read()
            r_file.close()
        except IOError:
            print "Warning: unable to access file: {0}".format(us_template) 

        if umbrellas == 2:
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
        if umbrellas == 1:
            try:
                w_file = open(new_restraints, "w")
                tbuffer = tbuffer.replace("@val1@", str(rstr_val_1))
                tbuffer = tbuffer.replace("@val1l@", str(rstr_val_1-90))
                tbuffer = tbuffer.replace("@val1h@", str(rstr_val_1+90))
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

