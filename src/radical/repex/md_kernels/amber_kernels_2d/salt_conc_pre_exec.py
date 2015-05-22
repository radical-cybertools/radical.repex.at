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

#-----------------------------------------------------------------------------------------------------------------------------------

def get_historical_data(history_name, data_path=os.getcwd()):
    """Retrieves temperature and potential energy from simulation output file .history file.
    This file is generated after each simulation run. The function searches for directory 
    where .history file recides by checking all computeUnit directories on target resource.

    Arguments:
    history_name - name of .history file for a given replica. 

    Returns:
    data[0] - temperature obtained from .history file
    data[1] - potential energy obtained from .history file
    path_to_replica_folder - path to computeUnit directory on a target resource where all
    input/output files for a given replica recide.
       Get temperature and potential energy from mdinfo file.

    ACTUALLY WE ONLY NEED THE POTENTIAL FROM HERE. TEMPERATURE GOTTA BE OBTAINED FROM THE PROPERTY OF THE REPLICA OBJECT.
    """

    home_dir = os.getcwd()
    os.chdir(data_path)

    temp = 0.0    #temperature
    eptot = 0.0   #potential
    try:
        f = open(history_name)
        lines = f.readlines()
        f.close()
        path_to_replica_folder = os.getcwd()
        for i in range(len(lines)):
            #if "TEMP(K)" in lines[i]:
            #    temp = float(lines[i].split()[8])
            if "EPtot" in lines[i]:
                eptot = float(lines[i].split()[8])
    except:
        pass

    os.chdir(home_dir)
    return eptot, path_to_replica_folder

#-----------------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    """This module calculates one swap matrix column for replica and writes this column to 
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
    # INITIAL REPLICA TEMPERATURE:
    init_temp = float(data["init_temp"])

    # AMBER PATH ON THIS RESOURCE:
    amber_path = data["amber_path"]

    # SALT CONCENTRATION FOR ALL REPLICAS
    all_salt_conc = (data["all_salt_ctr"])
    all_temperature = (data["all_temp"])

    # PATH TO SHARED INPUT FILES (to get ala10.prmtop)
    r_old_path = data["r_old_path"]

    pwd = os.getcwd()

    # getting history data for self
    history_name = base_name + "_" + str(replica_id) + "_" + str(replica_cycle) + ".mdinfo"
    replica_energy, path_to_replica_folder = get_historical_data( history_name, "../staging_area" )

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
    for j in range(replicas):
        energy_history_name = base_name + "_" + str(j) + "_" + str(replica_cycle) + "_energy.mdinfo"
        energy_input_name = base_name + "_" + str(j) + "_" + str(replica_cycle) + "_energy.mdin"

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
                f.write(line.replace("@salt@",all_salt_conc[j]))
            elif "@temp@" in line:
                f.write(line.replace("@temp@",all_temperature[j]))
            else:
                f.write(line)
        f.close()
        
        line = ' -O -i ' + energy_input_name + ' -p ' + prmtop_name + ' -c ' + new_coor + ' -inf ' + energy_history_name + '\n'
        f_groupfile.write(line)
    f_groupfile.close()

    