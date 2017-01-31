"""
.. module:: radical.repex.remote_application_modules.ram_amber.matrix_calculator_temp_ex
.. moduleauthor::  <antons.treikalis@gmail.com>
.. moduleauthor::  <haoyuan.chen@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import json
import math
import time
import fcntl
import shutil

#-------------------------------------------------------------------------------

def get_historical_data(replica_path, history_name):
    """reads potential energy from a given .mdinfo file

    Args:
        replica_path - path to replica directory in RP's staging_area

        history_name - name of .mdinfo file

    Returns:
        temp - temperature
        
        eptot - potential energy
    """

    home_dir = os.getcwd()
    if replica_path is not None:
        path = "../staging_area" + replica_path
        try:
            os.chdir(path)
        except:
            raise

    temp = 0.0    #temperature
    eptot = 0.0   #potential

    try:
        f = open(history_name)
        lines = f.readlines()
        f.close()
        for i,j in enumerate(lines):
            if "TEMP(K)" in lines[i]:
                temp = float(lines[i].split()[8])
            elif "EPtot" in lines[i]:
                eptot = float(lines[i].split()[8])
    except:
        os.chdir(home_dir)
        raise 

    os.chdir(home_dir)
    
    return temp, eptot

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    """This RAM is executed after Amber call to obtain data needed to populate 
    a column of a swap matrix for this replica.

    For this replica we read .mdinfo file and obtain energy values.
    Next, we write all necessary data to history_info_temp.dat file, which
    is located in staging_area of this pilot.

    Note: there is only a single instance of history_info_temp.dat file and 
    each CU associated with some replica is writing to this file (we use locks).
    Then, CU responsible for exchange calculations reads from that file.
    """

    json_data = sys.argv[1]
    data=json.loads(json_data)

    replica_id       = data["rid"]
    replica_cycle    = data["replica_cycle"]
    current_cycle    = data["current_cycle"]
    base_name        = data["base_name"]
    replicas         = int(data["replicas"])
    amber_parameters = data["amber_parameters"]
    new_restraints   = data["new_restraints"]
    rstr_vals        = data["rstr_vals"]
    init_temp        = data["init_temp"]
    
    history_name = base_name + "_" + replica_id + "_" + replica_cycle + ".mdinfo"

    #---------------------------------------------------------------------------
    success = 0
    attempts = 0
    while (success == 0):
        try:
            replica_temp, replica_energy = get_historical_data(None, history_name)
            print "Got history data for self!"
            success = 1
        except:
            print "Waiting for self (history file)"
            time.sleep(1)
            attempts += 1
            if attempts > 10:
                replica_temp   = -1.0
                replica_energy = -1.0
                print "MD run failed for replica {0}".format(replica_id)
            pass

    print "rstr_vals: "
    print rstr_vals

    history_str = str(replica_id) + " " + \
                  str(init_temp) + " " + \
                  str(replica_energy) + " " + \
                  str(new_restraints) + " "

    for val in rstr_vals:
        history_str += str(val) + " "
    history_str += "\n"

    print "history_str: {0}".format(history_str)
 
    pwd = os.getcwd()
    size = len(pwd)-1
    path = pwd
    for i in range(0,size):
        if pwd[size-i] != '/':
            path = path[:-1]
        else:
            break

    path += "staging_area/history_info_temp.dat" 
    try:
        with open(path, "a") as g:
            fcntl.flock(g, fcntl.LOCK_EX)
            g.write(history_str)
            fcntl.flock(g, fcntl.LOCK_UN)
    except:
        raise

