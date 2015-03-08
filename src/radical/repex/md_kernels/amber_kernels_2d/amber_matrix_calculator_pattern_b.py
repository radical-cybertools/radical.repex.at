"""
.. module:: radical.repex.md_kernels.amber_kernels_tex.amber_matrix_calculator_scheme_2
.. moduleauthor::  <antons.treikalis@rutgers.edu>
.. moduleauthor::  <haoyuan.chen@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys

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
    history_name - name of .history file for a given replica. 

    Returns:
    data[0] - temperature obtained from .history file
    data[1] - potential energy obtained from .history file
    path_to_replica_folder - path to computeUnit directory on a target resource where all
    input/output files for a given replica recide.
       Get temperature and potential energy from mdinfo file.
    """

    home_dir = os.getcwd()
    os.chdir("../staging_area")

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
        #print "history file %s found!" % ( history_name ) 
    except:
        pass 

    os.chdir("../")
    os.chdir(home_dir)
    
    return temp, eptot, path_to_replica_folder

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
    #matrix_col = "matrix_column_%s_%s.dat" % ( replica_id, replica_cycle ) 

    # getting history data for self
    history_name = base_name + "_" + replica_id + "_" + replica_cycle + ".mdinfo"
    #print "history name: %s" % history_name
    replica_temp, replica_energy, path_to_replica_folder = get_historical_data( history_name )

    # getting history data for all replicas
    # we rely on the fact that last cycle for every replica is the same, e.g. == replica_cycle
    # but this is easily changeble for arbitrary cycle numbers
    temperatures = [0.0]*replicas
    energies = [0.0]*replicas
    for j in range(replicas):
        history_name = base_name + "_" + str(j) + "_" + replica_cycle + ".mdinfo" 
        try:
            rj_temp, rj_energy, temp = get_historical_data( history_name )
            temperatures[j] = rj_temp
            energies[j] = rj_energy
        except:
             pass 

    # init swap column
    swap_column = [0.0]*replicas

    for j in range(replicas):        
        swap_column[j] = reduced_energy(temperatures[j], replica_energy)

    try:
        #r_file = open( (os.path.join(pwd, matrix_col) ), "w")
        for item in swap_column:
            #r_file.write( str(item) + " " )
            print item,
        # writing path to replica folder
        print str(path_to_replica_folder).rstrip()

        #r_file.write("\n")
        #r_file.write( str(path_to_replica_folder) )
        #r_file.close()
    except IOError:
        print 'Warning: unable to create column file %s for replica %s' % (matrix_col, replica_id) 


