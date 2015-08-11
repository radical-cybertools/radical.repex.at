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
def reduced_energy(temperature, potential):
    """Calculates reduced energy.

    Arguments:
    temperature - replica temperature
    potential - replica potential energy

    Returns:
    reduced enery of replica
    """
    kb = 0.0019872041    #boltzmann const in kcal/mol
    if temperature != 0:
        beta = 1. / (kb*temperature)
    else:
        beta = 1. / kb     
    return float(beta * potential)

#-------------------------------------------------------------------------------
#
def get_historical_data(history_name, data_path=os.getcwd()):
    """Retrieves temperature and potential energy from simulation output file .history file.
    This file is generated after each simulation run. The function searches for directory 
    where .history file recides by checking all computeUnit directories on target resource.

    Arguments:
    history_name - name of .history file for a given replica. 

    Returns:
    data[0] - temperature obtained from .history file
    data[1] - potential energy obtained from .history file
    path_to_replica_folder - path to computeUnit directory on a target resource 
    where all
    input/output files for a given replica recide.
       Get temperature and potential energy from mdinfo file.

    ACTUALLY WE ONLY NEED THE POTENTIAL FROM HERE. TEMPERATURE GOTTA BE OBTAINED 
    FROM THE PROPERTY OF THE REPLICA OBJECT.
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
        raise

    os.chdir(home_dir)
    return eptot, path_to_replica_folder

#-------------------------------------------------------------------------------
#
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
    init_salt = float(data["init_salt"])
    new_restraints = data["new_restraints"]

    # AMBER PATH ON THIS RESOURCE:
    amber_path = data["amber_path"]

    current_group_tsu = data["current_group_tsu"]

    r_old_path = data["r_old_path"]

    pwd = os.getcwd()

    #---------------------------------------------------------------------------

    temperatures = [0.0]*replicas  
    energies = [0.0]*replicas

    #for j in range(replicas):
    for j in current_group_tsu.keys():
        energy_history_name = base_name + "_" + str(j) + "_" + str(replica_cycle) + "_energy.mdinfo"
        try:
            rj_energy, path_to_replica_folder = get_historical_data( energy_history_name )
            temperatures[int(j)] = float(init_temp)
            energies[int(j)] = rj_energy
        except:
             raise

    # init swap column
    swap_column = [0.0]*replicas

    #for j in range(replicas):
    for j in current_group_tsu.keys():       
        swap_column[int(j)] = reduced_energy(temperatures[int(j)], energies[int(j)])

    #---------------------------------------------------------------------------
    # writing to file
    outfile = "matrix_column_{replica}_{cycle}.dat".format(cycle=replica_cycle, replica=replica_id )
    with open(outfile, 'w+') as f:
        row_str = ""
        for item in swap_column:        
            if len(row_str) != 0:
                row_str = row_str + " " + str(item)
            else:
                row_str = str(item)   
        row_str + " " + (str(path_to_replica_folder).rstrip())
        f.write(row_str)    
        f.write('\n')
        row_str = str(replica_id) + " " + str(replica_cycle) + " " + new_restraints + " " + str(init_temp) + " " + str(init_salt)
        f.write(row_str)
    f.close()
  
 