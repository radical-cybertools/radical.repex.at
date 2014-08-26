"""
.. module:: radical.repex.md_kernels.amber_kernels_tex.amber_matrix_calculator_scheme_4
.. moduleauthor::  <antons.treikalis@rutgers.edu>
.. moduleauthor::  <haoyuan.chen@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import re
import sys

#-----------------------------------------------------------------------------------------------------------------------------------

def alphanumeric_sorting(data_list):

    convert = lambda text: int(text) if text.isdigit() else text
    alphanumeric_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]

    return sorted(data_list, key = alphanumeric_key, reverse=True)

#-----------------------------------------------------------------------------------------------------------------------------------

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

#-----------------------------------------------------------------------------------------------------------------------------------

def get_historical_data(history_name):
    """Retrieves temperature and potential energy from simulation output file .history file.
    This file is generated after each simulation run. The function searches for directory 
    where .history file recides by checking all computeUnit directories on target resource.

    Arguments:
    history_name - name of .mdinfo file for a given replica. 

    Returns:
    replica_data  - list with important data
    replica_data[0] - temperature obtained from .mdinfo file
    replica_data[1] - potential energy obtained from .mdinfo file
    replica_data[2] - path to ComputeUnit directory on a target resource where all
    input/output files for a given replica recide (path_to_replica_folder)
    replica_data[3] - stopped_i_run
    """
    replica_data = []

    home_dir = os.getcwd()
    os.chdir("../")

    # getting all cu directories
    replica_dirs = []
    for name in os.listdir("."):
        if os.path.isdir(name):
            replica_dirs.append(name)    

    for directory in replica_dirs:
        os.chdir(directory)
        try:
            f = open(history_name)

            # at this point we have found replica directory
            # this is a basename for all restart files
            base_name = history_name[:-6] + "rst_"
            # all restart files in directory
            files = sorted([ f for f in os.listdir(home_dir) if f.startswith(base_name)])

            sorted_restart_files = alphanumeric_sorting(files)

            # obtaining a path to replica folder
            path_to_replica_folder = os.getcwd()

            #######################################
            # getting stopped_i_run
            hist_name = sorted_restart_files[0]
            
            i_run_list = []
            for char in reversed(hist_name):
                if char.isdigit():
                    i_run_list.append(char)
                else:
                    break

            reversed_i_run_list = []
            for i in reversed(i_run_list):
                reversed_i_run_list.append( str(i) )

            # sanity check
            print reversed_i_run_list

            stopped_i_run = ''
            for item in reversed_i_run_list:
                stopped_i_run = stopped_i_run + item
            #######################################    

            temp = 0.0    #temperature
            eptot = 0.0   #potential
            # reading data from mdinfo file, is this correct? does this file has latest pot and eng? 
            lines = f.readlines()
            f.close()
            for i in range(len(lines)):
                if "TEMP(K)" in lines[i]:
                    temp = float(lines[i].split()[8])
                elif "EPtot" in lines[i]:
                    eptot = float(lines[i].split()[8])          
        except:
            pass 
        os.chdir("../")
 
    os.chdir(home_dir)

    # populating replica_data list 
    replica_data.append(float(temp))
    replica_data.append(float(eptot))
    replica_data.append(path_to_replica_folder)
    replica_data.append(stopped_i_run)

    return replica_data

#-----------------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    """This module calculates one swap matrix column for replica and writes this column to 
    matrix_column_x_x.dat file. 
    """

    argument_list = str(sys.argv)
    replica_id = str(sys.argv[1])
    replica_cycle = str(sys.argv[2])
    replicas = int(str(sys.argv[3]))
    base_name = str(sys.argv[4])

    pwd = os.getcwd()
    matrix_col = "matrix_column_%s_%s.dat" % ( replica_id, replica_cycle ) 

    # getting history data for self
    # we use .mdinfo file in order to obtain  and latest restart files
    history_name = base_name + "_" + replica_id + "_" + replica_cycle + ".mdinfo"

    replica_data = get_historical_data( history_name )

    replica_temp = replica_data[0]
    replica_energy = replica_data[1]
    path_to_replica_folder = replica_data[2]
    stopped_i_run = replica_data[3]

    # getting history data for all replicas
    # we rely on the fact that last cycle for every replica is the same, e.g. == replica_cycle
    # but this is easily changeble for arbitrary cycle numbers
    temperatures = [0.0]*replicas
    energies = [0.0]*replicas
    for j in range(replicas):
        history_name = base_name + "_" + str(j) + "_" + replica_cycle + ".mdinfo" 
        try:
            rj_data = get_historical_data( history_name )
            temperatures[j] = rj_data[0]
            energies[j] = rj_data[1]
        except:
             pass 

    # init swap column
    swap_column = [0.0]*replicas

    for j in range(replicas):        
        swap_column[j] = reduced_energy(temperatures[j], replica_energy)

    try:
        # writing matrix column data out
        r_file = open( (os.path.join(pwd, matrix_col) ), "w")
        for item in swap_column:
            r_file.write( str(item) + " " )
        # writing path to replica folder
        r_file.write("\n")
        r_file.write( str(path_to_replica_folder) )
        # writing stopped_i_run
        r_file.write("\n")
        r_file.write( str(stopped_i_run) )
        r_file.close()
    except IOError:
        print 'Warning: unable to create column file %s for replica %s' % (matrix_col, replica_id) 


