"""
.. module:: radical.repex.remote_application_modules.ram_amber.salt_conc_pre_exec
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
def get_historical_data(replica_path, history_name):
    """reads potential energy from a given .mdinfo file

    Args:
        replica_path - path to replica directory in RP's staging_area

        history_name - name of .mdinfo file

    Returns:
        eptot - potential energy

        path_to_replica_folder - path to directory of a given replica in RP's 
        staging area
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
        #path_to_replica_folder = os.getcwd()
        path_to_replica_folder = path
        for i,j in enumerate(lines):
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
    """This RAM is executed after MD simulation for a given replica is done and
    before we call Amber for Single Point Energy (SPE) calculations. This RAM 
    prepares a groupfile to calculate SPE.
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
    amber_path        = data["amber_path"]
    current_group_tsu = data["current_group_tsu"]
    r_old_path        = data["r_old_path"]

    pwd = os.getcwd()

    # getting history data for self
    history_name = base_name + "_" + str(replica_id) + "_" + str(replica_cycle) + ".mdinfo"
    replica_path = "/replica_{0}/".format(str(replica_id))
    replica_energy, path_to_replica_folder = get_historical_data( replica_path, history_name )

    # FILE ala10_remd_X_X.rst IS IN DIRECTORY WHERE THIS SCRIPT IS LAUNCHED AND CEN BE REFERRED TO AS:
    new_coor_file = "{0}_{1}_{2}.rst".format(base_name, replica_id, replica_cycle)
    new_coor = path_to_replica_folder + new_coor_file

    f_groupfile = file('groupfile','w')
    # call amber to run 1-step energy calculation
    for j in current_group_tsu.keys():

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
                f.write(line.replace("@salt@",current_group_tsu[j][1]))
            elif "@temp@" in line:
                f.write(line.replace("@temp@",current_group_tsu[j][0]))
            elif "@disang@" in line:
                f.write(line.replace("@disang@",current_group_tsu[j][2]))
            elif "@irest@" in line:
                line = line.replace("@irest@","0")
                f.write(line)
            elif "@ntx@" in line:
                line = line.replace("@ntx@","1")
                f.write(line)
            else:
                f.write(line)
        f.close()
        
        line = ' -O -i ' + energy_input_name + ' -p ' + prmtop_name + ' -c ' + new_coor + ' -inf ' + energy_history_name + '\n'
        f_groupfile.write(line)
    f_groupfile.close()

