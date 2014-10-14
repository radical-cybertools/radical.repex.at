"""
.. module:: radical.repex.md_kernels.amber_kernels_salt.amber_matrix_calculator_pattern_b
.. moduleauthor::  <haoyuan.chen@rutgers.edu>
.. moduleauthor::  <antons.treikalis@rutgers.edu>
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

    ------------Haoyuan 2014/10/13--------------
    This function obtain temperature and potential from mdinfo files, which is not the way to go in the long run.

    The newly added "get_temperature" function will get temperature from input file (in this way we get the correct temperature 
    we want, rather than the instanenous temperature.

    The "get_potential" function will try to call AMBER to compute potential.

    Further code reorganization required when the new functions are done...

    """
    home_dir = os.getcwd()
    os.chdir("../")

    # getting all cu directories
    replica_dirs = []
    for name in os.listdir("."):
        if os.path.isdir(name):
            replica_dirs.append(name)    

    temp = 0.0    #temperature
    eptot = 0.0   #potential
    for directory in replica_dirs:
         os.chdir(directory)
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
             print "history file %s found!" % ( history_name ) 
         except:
             pass 
         os.chdir("../")
 
    os.chdir(home_dir)
    return temp, eptot, path_to_replica_folder

#-----------------------------------------------------------------------------------------------------------------------------------

def get_temperature(input_name):
    """This function gets replica temperature from input.
       Actually I think there's a way we can get the temperature value passed from some simulation objects to here.
       That's gonna be a better way to do.
    """

    home_dir = os.getcwd()
    os.chdir("../")

    # getting all cu directories
    replica_dirs = []
    for name in os.listdir("."):
        if os.path.isdir(name):
            replica_dirs.append(name)

    temp = 0.0    #temperature
    for directory in replica_dirs:
         os.chdir(directory)
         try:
             f = open(input_name)
             lines = f.readlines()
             f.close()
             path_to_replica_folder = os.getcwd()
             for i in range(len(lines)):
                 if "temp0" in lines[i]:
                     temp_idx = lines[i].index("temp0")+5
                     temp = float(lines[i][temp_idx:].split(",")[0].replace("=",""))    #doesn't look very good but works for now
             print "input file %s found!" % ( input_name )
         except:
             pass
         os.chdir("../")

    os.chdir(home_dir)
    return temp, path_to_replica_folder

#-----------------------------------------------------------------------------------------------------------------------------------

def get_potential(history_name):
    """Doesn't change too much from the get_historical_data function but when calling this function,
       the history_name should be the mdinfo generated in the single-point energy calculation which called Amber.
    """

    home_dir = os.getcwd()
    os.chdir("../")

    # getting all cu directories
    replica_dirs = []
    for name in os.listdir("."):
        if os.path.isdir(name):
            replica_dirs.append(name)

    eptot = 0.0   #potential
    for directory in replica_dirs:
         os.chdir(directory)
         try:
             f = open(history_name)
             lines = f.readlines()
             f.close()
             path_to_replica_folder = os.getcwd()
             for i in range(len(lines)):
                 if "EPtot" in lines[i]:
                     eptot = float(lines[i].split()[8])
             print "history file %s found!" % ( history_name )
         except:
             pass
         os.chdir("../")

    os.chdir(home_dir)
    return eptot, path_to_replica_folder

#-----------------------------------------------------------------------------------------------------------------------------------

def single_point_energy():

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
    history_name = base_name + "_" + replica_id + "_" + replica_cycle + ".mdinfo"
    print "history name: %s" % history_name
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
        r_file = open( (os.path.join(pwd, matrix_col) ), "w")
        for item in swap_column:
            r_file.write( str(item) + " " )
        # writing path to replica folder
        r_file.write("\n")
        r_file.write( str(path_to_replica_folder) )
        r_file.close()
    except IOError:
        print 'Warning: unable to create column file %s for replica %s' % (matrix_col, replica_id) 


