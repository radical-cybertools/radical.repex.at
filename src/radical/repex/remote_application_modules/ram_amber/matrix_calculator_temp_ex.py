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
        #path_to_replica_folder = os.getcwd()
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

    replica_id       = int(data["rid"])
    replica_cycle    = data["replica_cycle"]
    base_name        = data["base_name"]
    replicas         = int(data["replicas"])
    amber_parameters = data["amber_parameters"]
    new_restraints   = data["new_restraints"]
    init_temp        = data["init_temp"]
    temp_group       = data["current_group"]

    current_group_temp = data["current_group_temp"]

    tmp = list()
    for i in temp_group:
        tmp.append(int(i))
    current_group = sorted(tmp) 

    history_name = base_name + "_" + str(replica_id) + "_" + replica_cycle + ".mdinfo"
    swap_column  = [0.0]*replicas

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
            if attempts > 5:
                #---------------------------------------------------------------
                # writing to file
                try:
                    outfile = "matrix_column_{replica}_{cycle}.dat".format(cycle=replica_cycle, replica=str(replica_id) )
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

    #---------------------------------------------------------------------------
    # getting history data for all replicas
    # we rely on the fact that last cycle for every replica is the same, 
    # e.g. == replica_cycle
    # but this is easily changeble for arbitrary cycle numbers
    temperatures = [0.0]*replicas
    energies = [0.0]*replicas

    # for self
    temperatures[replica_id] = float(current_group_temp[str(replica_id)])
    energies[replica_id] = replica_energy

    history_str = str(replica_id) + " " + str(replica_energy) + " "

    first_id = current_group[0]
    gr_size  = len(current_group)
    if replica_id == first_id:
        right_id = first_id + 1
    else if replica_id == (gr_size-1):
        left_id  = replica_id - 1
    else:
        right_id = replica_id + 1
        left_id  = replica_id - 1

    pwd = os.getcwd()
    print pwd
    size = len(pwd)-1
    path = pwd
    for i in range(0,size):
        if pwd[size-i] != '/':
            path = path[:-1]
        else:
            break
    print path

    # we use fifo_self fo sends and fifo_right / fifo_left for receives
    if replica_id == first_id:

        fifo_self  = path + "replica" + str(replica_id) + ".fifo"
        fifo_right = path + "replica" + str(right_id)   + ".fifo"

        r = os.path.exists(fifo_self)
        if r == False:
            print "making fifo_self, rid {0}".format(replica_id)
            os.mkfifo(fifo_self)

        # sending data to the right
        cmd = "echo " + history_str + " > " + fifo_self
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        process.wait()
        out, err = process.communicate()

        # receiving data from the right
        r = os.path.exists(fifo_right)
        if r == False:
            print "making fifo_right, rid {0}".format(replica_id)
            os.mkfifo(fifo_right)

        cmd = "cat < " + fifo_right
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        process.wait()
        history_str_full, err1 = process.communicate()
        history_str_full = history_str_full.rstrip()

        if os.path.exists(fifo_self):
            os.unlink(fifo_self)

    else if replica_id == (gr_size-1):

        fifo_self  = path + "replica" + str(replica_id) + ".fifo"
        fifo_left = path + "replica" + str(left_id)   + ".fifo"

        # receiving data from the left
        r = os.path.exists(fifo_left)
        if r == False:
            print "making fifo_left, rid {0}".format(replica_id)
            os.mkfifo(fifo_left)

        cmd = "cat < " + fifo_left
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        process.wait()
        history_str_tmp, err = process.communicate()

        history_str_full = history_str_tmp.rstrip() + history_str

        r = os.path.exists(fifo_self)
        if r == False:
            print "making fifo_self, rid {0}".format(replica_id)
            os.mkfifo(fifo_self)

        # sending data to the left
        cmd = "echo " + history_str_full + " > " + fifo_self
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        process.wait()
        out1, err1 = process.communicate()

        if os.path.exists(fifo_self):
            os.unlink(fifo_self)

    else:

        fifo_left   = path + "replica" + str(left_id)    + ".fifo"
        fifo_right  = path + "replica" + str(right_id)   + ".fifo"
        fifo_self_l = path + "replica" + str(replica_id) + "l.fifo"
        fifo_self_r = path + "replica" + str(replica_id) + "r.fifo"

        # receiving data from the left
        r = os.path.exists(fifo_left)
        if r == False:
            print "making fifo_left, rid {0}".format(replica_id)
            os.mkfifo(fifo_left)

        cmd = "cat < " + fifo_left
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        process.wait()
        history_str_tmp, err = process.communicate()

        history_str_tmp = history_str_tmp.rstrip() + history_str

        r = os.path.exists(fifo_self_r)
        if r == False:
            print "making fifo_self_r, rid {0}".format(replica_id)
            os.mkfifo(fifo_self_r)

        # sending data to the right
        cmd = "echo " + history_str_tmp + " > " + fifo_self_r
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        process.wait()
        out1, err1 = process.communicate()

        #-----------------------------------------------------------------------
        # receiving data from the right
        r = os.path.exists(fifo_right)
        if r == False:
            print "making fifo_right, rid {0}".format(replica_id)
            os.mkfifo(fifo_right)

        cmd = "cat < " + fifo_right
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        process.wait()
        history_str_full, err = process.communicate()
        history_str_full = history_str_full.rstrip()

        r = os.path.exists(fifo_self_l)
        if r == False:
            print "making fifo_self_l, rid {0}".format(replica_id)
            os.mkfifo(fifo_self_l)

        # sending data to the left
        cmd = "echo " + history_str_full + " > " + fifo_self_l
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        process.wait()
        out1, err1 = process.communicate()

        if os.path.exists(fifo_self_r):
            os.unlink(fifo_self_r)

        if os.path.exists(fifo_self_l):
            os.unlink(fifo_self_l)

    print "history_str_full: {0}".format(history_str_full)
    h_list = history_str_full.split()

    history_data = {}
    for idx,val in enumerate(h_list):
        if (idx % 2) == 0:
            history_data[int(h_list[idx])] = h_list[idx+1]

    for j in current_group:
        # for self already processed
        if j != replica_id:
            temperatures[j] = float(current_group_temp[str(j)])
            energies[j] = history_data[j]

    print "Got history data for other replicas in current group!"

    swap_column = [0.0]*replicas 
    for j in current_group:      
        swap_column[j] = reduced_energy(temperatures[j], replica_energy)

    #---------------------------------------------------------------------------
    # writing to file
    try:
        outfile = "matrix_column_{replica}_{cycle}.dat".format(cycle=replica_cycle, replica=str(replica_id) )
        with open(outfile, 'w+') as f:
            row_str = ""
            for item in swap_column:
                if len(row_str) != 0:
                    row_str = row_str + " " + str(item)
                else:
                    row_str = str(item)
            f.write(row_str)
            f.write('\n')
            row_str = str(replica_id) + " " + replica_cycle + " " + new_restraints + " " + init_temp + " _"
            f.write(row_str)
        f.close()

    except IOError:
        print 'Error: unable to create column file {0} for replica {1}'.format(outfile, replica_id)
