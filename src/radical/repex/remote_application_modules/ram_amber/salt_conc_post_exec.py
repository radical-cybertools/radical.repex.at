"""
.. module:: radical.repex.remote_application_modules.ram_amber.salt_conc_post_exec
.. moduleauthor::  <antons.treikalis@gmail.com>
.. moduleauthor::  <haoyuan.chen@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import json
import time
import socket

#-------------------------------------------------------------------------------
#
def reduced_energy(temperature, potential):
    """Calculates reduced energy.

    Args:
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
    """reads potential energy from a given .mdinfo file

    Args:
        data_path - path to replica directory in RP's staging_area

        history_name - name of .mdinfo file

    Returns:
        eptot - potential energy

        path_to_replica_folder - path to CU sandbox where MD simulation was 
        executed
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
        for i,j in enumerate(lines):
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
    """This RAM is executed after Amber call to calculate single point energies 
    (using Amber' group file feature).
    For each replica we read _energy.mdinfo file and obtain energy values.
    Next we populate lists of temperatures and energies and calculate reduced 
    energy, which is used to populate a column of a swap matrix for a given 
    replica. 
    """
   
    json_data = sys.argv[1]
    data=json.loads(json_data)

    replica_id        = int(data["rid"])
    replica_cycle     = int(data["replica_cycle"])
    replicas          = int(data["replicas"])
    base_name         = data["base_name"]
    prmtop_name       = data["amber_parameters"]
    mdin_name         = data["amber_input"]
    init_temp         = float(data["init_temp"])
    init_salt         = float(data["init_salt"])
    new_restraints    = data["new_restraints"]
    amber_path        = data["amber_path"]
    current_group_tsu = data["current_group_tsu"]
    r_old_path        = data["r_old_path"]

    pwd = os.getcwd()

    #---------------------------------------------------------------------------

    temperatures = [0.0]*replicas  
    energies = [0.0]*replicas

    for j in current_group_tsu.keys():
        success = 0
        attempts = 0
        while (success == 0):
            energy_history_name = base_name + "_" + str(j) + "_" + str(replica_cycle) + "_energy.mdinfo"
            try:
                rj_energy, path_to_replica_folder = get_historical_data( energy_history_name )
                temperatures[int(j)] = float(init_temp)
                energies[int(j)] = rj_energy
                success = 1
            except:
                attempts += 1
                print "Waiting for replica: %s" % j
                time.sleep(1)
                if attempts > 5:
                    temperatures[int(j)] = -1.0
                    energies[int(j)] = -1.0
                    path_to_replica_folder = '/'
                    success = 1
                    print "Replica {0} failed, initialized temperatures[j] and energies[j] to -1.0".format(j)
                pass

    swap_column = [0.0]*replicas
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
  
 