"""
.. module:: radical.repex.md_kernels.amber_kernels_salt.amber_matrix_calculator_pattern_b
.. moduleauthor::  <haoyuan.chen@rutgers.edu>
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import json
import os,sys,socket,time

#-------------------------------------------------------------------------------
#
def get_historical_data(replica_path, history_name):
    """Retrieves temperature and potential energy from simulation output file 
    .history file. This file is generated after each simulation run. The 
    function searches for directory where .history file recides by checking all 
    computeUnit directories on target resource.

    Arguments:
    history_name - name of .history file for a given replica. 

    Returns:
    data[0] - temperature obtained from .history file
    data[1] - potential energy obtained from .history file
    path_to_replica_folder - path to computeUnit directory on a target resource 
    where all input/output files for a given replica recide.
       Get temperature and potential energy from mdinfo file.
    """

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
        #path_to_replica_folder = os.getcwd()
        path_to_replica_folder = path
        for i in range(len(lines)):
            if "EPtot" in lines[i]:
                eptot = float(lines[i].split()[8])
    except:
        os.chdir(home_dir)
        raise 

    os.chdir(home_dir)
    
    return eptot, path_to_replica_folder

#-------------------------------------------------------------------------------
#
if __name__ == '__main__':
    """This module calculates one swap matrix column for replica and writes this 
    column to 
    matrix_column_x_x.dat file. 
    """

    json_data = sys.argv[1]
    data=json.loads(json_data)

    replica_id = int(data["replica_id"])
    replica_cycle = int(data["replica_cycle"])
    replicas = int(data["replicas"])
    base_name = data["base_name"]
    prmtop_name = data["amber_parameters"]
    mdin_name = data["amber_input"]
    amber_path = data["amber_path"]
    all_salts = data["all_salts"]

    # PATH TO SHARED INPUT FILES (to get ala10.prmtop)
    r_old_path = data["r_old_path"]

    pwd = os.getcwd()

    # getting history data for self
    history_name = base_name + "_" + str(replica_id) + "_" + str(replica_cycle) + ".mdinfo"
    #replica_path = "/replica_%s/" % (str(replica_id))
    replica_path = "/"
    replica_energy, path_to_replica_folder = get_historical_data( replica_path, history_name )

    # FILE ala10_remd_X_X.rst IS IN DIRECTORY WHERE THIS SCRIPT IS LAUNCHED AND CEN BE REFERRED TO AS:
    new_coor_file = "%s_%d_%d.rst" % (base_name, replica_id, replica_cycle)
    new_coor = path_to_replica_folder + "/" + new_coor_file

    # getting history data for all replicas
    # we rely on the fact that last cycle for every replica is the same, e.g. == replica_cycle
    # but this is easily changeble for arbitrary cycle numbers
    temperatures = [0.0]*replicas   #need to pass the replica temperature here
    energies = [0.0]*replicas

    f_groupfile = file('groupfile','w')
    # call amber to run 1-step energy calculation
    #for j in range(replicas):
    for j in all_salts.keys():

        energy_history_name = base_name + "_" + j + "_" + str(replica_cycle) + "_energy.mdinfo"
        energy_input_name = base_name + "_" + j + "_" + str(replica_cycle) + "_energy.mdin"

        input_template = mdin_name
        f = file(input_template,'r')
        input_data = f.readlines()
        f.close()

        # change nstlim to be zero
        f = file(energy_input_name,'w')
        for line in input_data:
            if "@nstlim@" in line:
                f.write(line.replace("@nstlim@","0"))
            elif "@salt@" in line:
                f.write(line.replace("@salt@",current_group_tsu[j][0]))
            elif "@irest@" in line:
                line = line.replace("@irest@","1")
                line = line.replace("@ntx@","5")
                f.write(line)
            else:
                f.write(line)
        f.close()
        
        line = ' -O -i ' + energy_input_name + ' -p ' + prmtop_name + ' -c ' + new_coor + ' -inf ' + energy_history_name + '\n'
        f_groupfile.write(line)
    f_groupfile.close()

