"""
.. module:: radical.repex.md_kernels.amber_kernels_tex.matrix_calculator_tex
.. moduleauthor::  <antons.treikalis@rutgers.edu>
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

def reduced_energy(temperature, potential):
   
    kb = 0.0019872041    #boltzmann const in kcal/mol
    if temperature != 0:
        beta = 1. / (kb*temperature)
    else:
        beta = 1. / kb     
    return float(beta * potential)

#-------------------------------------------------------------------------------

def get_historical_data(replica_path, history_name):
    
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
        history_str += val + " "
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

    path += "staging_area/history_info.dat" 
    try:
        with open(path, "a") as g:
            fcntl.flock(g, fcntl.LOCK_EX)
            g.write(history_str)
            fcntl.flock(g, fcntl.LOCK_UN)
    except:
        raise

