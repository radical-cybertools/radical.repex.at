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
    if replica_path != None:
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
        path_to_replica_folder = os.getcwd()
        for i in range(len(lines)):
            if "TEMP(K)" in lines[i]:
                temp = float(lines[i].split()[8])
            elif "EPtot" in lines[i]:
                eptot = float(lines[i].split()[8])
    except:
        os.chdir(home_dir)
        raise 

    os.chdir(home_dir)
    
    return temp, eptot, path_to_replica_folder

#-------------------------------------------------------------------------------

if __name__ == '__main__':

    json_data = sys.argv[1]
    data=json.loads(json_data)

    replica_id = data["rid"]
    replica_cycle = data["replica_cycle"]
    base_name = data["base_name"]
    replicas = int(data["replicas"])
    amber_parameters = data["amber_parameters"]
    new_restraints = data["new_restraints"]
    init_temp = data["init_temp"]
    temp_group = data["current_group"]

    current_group_temp = data["current_group_temp"]

    current_group = []
    for i in temp_group:
        current_group.append(int(i))
     
    history_name = base_name + "_" + replica_id + "_" + replica_cycle + ".mdinfo"
    swap_column  = [0.0]*replicas

    #---------------------------------------------------------------------------
    # copy history_name to staging_area/replica_x 
    pwd = os.getcwd()
    replica_path = "/replica_%s/" % (replica_id)
    src = pwd + "/" + history_name

    size = len(pwd)-1
    path = pwd
    for i in range(0,size):
        if pwd[size-i] != '/':
            path = path[:-1]
        else:
            break

    dst_path = path + "staging_area" + replica_path
    dst = dst_path + history_name

    if not os.path.exists(dst_path):
        os.makedirs(dst_path)

    try:
        shutil.copyfile(src, dst)
        print "Success copying history_name to staging_area!"
    except:
        print "Fail copying history_name to staging_area..."
        raise

    #---------------------------------------------------------------------------
    success = 0
    attempts = 0
    while (success == 0):
        try:
            replica_temp, replica_energy, path_to_replica_folder = get_historical_data(None, history_name)
            print "Got history data for self!"
            success = 1
        except:
            print "Waiting for self (history file)"
            time.sleep(1)
            attempts += 1
            if attempts > 5:
                #---------------------------------------------------------------
                # writing to file
                try:
                    outfile = "matrix_column_{replica}_{cycle}.dat".format(cycle=replica_cycle, replica=replica_id )
                    with open(outfile, 'w+') as f:
                        row_str = ""
                        for item in swap_column:
                            if len(row_str) != 0:
                                row_str = row_str + " " + str(-1.0)
                            else:
                                row_str = str(-1.0)
                            f.write(row_str)
                            f.write('\n')
                            row_str = str(replica_id) + " " + str(replica_cycle) + " " + new_restraints + " " + str(init_temp)
                            f.write(row_str)
                        f.close()
                    success = 1
                except IOError:
                    print "Error: unable to create column file {0} for replica {1}".format(outfile, replica_id)
                print "MD run failed for replica {0}, matrix_swap_column_x_x.dat populated with zeros".format(replica_id)
            pass

    # getting history data for all replicas
    # we rely on the fact that last cycle for every replica is the same, e.g. == replica_cycle
    # but this is easily changeble for arbitrary cycle numbers
    temperatures = [0.0]*replicas
    energies = [0.0]*replicas

    # for self
    temperatures[int(replica_id)] = float(current_group_temp[replica_id])
    energies[int(replica_id)] = replica_energy

    for j in current_group:
        # for self already processed
        if j != int(replica_id):
            success = 0
            attempts = 0
            history_name = base_name + "_" + str(j) + "_" + replica_cycle + ".mdinfo" 
            replica_path = "/replica_%s/" % (str(j))
            while (success == 0):
                try:
                    rj_temp, rj_energy, temp = get_historical_data(replica_path, history_name)
                    temperatures[j] = float(current_group_temp[str(j)])
                    energies[j] = rj_energy
                    success = 1
                    print "Success processing replica: %s" % j
                except:
                    print "Waiting for replica: %s" % j
                    time.sleep(1)
                    attempts += 1
                    # some of the replicas in current group failed
                    # set temperature and energy for this replicas as -1.0
                    if attempts > 100:
                        temperatures[j] = -1.0
                        energies[j] = -1.0
                        success = 1
                        print "Replica {0} failed, initialized temperatures[j] and energies[j] to -1.0".format(j)
                    pass

    print "Got history data for other replicas in current group!"

    swap_column = [0.0]*replicas 
    for j in current_group:      
        swap_column[j] = reduced_energy(temperatures[j], replica_energy)

    #---------------------------------------------------------------------------
    # writing to file
    try:
        outfile = "matrix_column_{replica}_{cycle}.dat".format(cycle=replica_cycle, replica=replica_id )
        with open(outfile, 'w+') as f:
            row_str = ""
            for item in swap_column:
                if len(row_str) != 0:
                    row_str = row_str + " " + str(item)
                else:
                    row_str = str(item)
            f.write(row_str)
            f.write('\n')
            row_str = replica_id + " " + replica_cycle + " " + new_restraints + " " + init_temp + " _"
            f.write(row_str)
        f.close()

    except IOError:
        print 'Error: unable to create column file %s for replica %s' % (outfile, replica_id)

    
