"""
.. module:: radical.repex.namd_kernels.namd_matrix_calculator_scheme_4
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import re
import sys

#-----------------------------------------------------------------------------------------------------------------------------------

def alphanumeric_sorting(data_list):
    """This function sorts a list of strings composed of letters and digits in "logical" order, 
    that is string containing number 1900 will appear after the string containing number 300 
    and not the other way around.

    Arguments:
    data_list - list of strings containing both letters and digits

    Returns:
    data_list - sorted list in descending order
    """

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
    kb = 0.0019872041
    # check for division by zero
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
    history_name - name of first generated .history file for a given replica, e.g. where i_run = 0 

    Returns:
    replica_data - list with important data
    replica_data[0] - temperature obtained from .history file
    replica_data[1] - potential energy obtained from .history file
    replica_data[2] - path to ComputeUnit directory on a target resource where all input/output
     files for a given replica recide.
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
            history_f = open(history_name)
            print "CHECK 1"
            print history_name
            history_f.close()

            current_dir = os.getcwd()
            print "current dir:"
            print current_dir
            # at this point we have found replica directory
            base_name = history_name[:-10]
            # all files in directory
            files = sorted([ f for f in os.listdir(current_dir) if f.startswith(base_name)])

            history_files = []
            coor_files = []
            vel_files = []
            xsc_files = []
            print "CHECK 2"
            for item in files:
                if item.endswith('.history'):
                    history_files.append(item)
                elif item.endswith('.restart.coor'):
                    coor_files.append(item)
                elif item.endswith('.restart.vel'):
                    vel_files.append(item)
                elif item.endswith('.restart.xsc'):
                    xsc_files.append(item)

            sorted_history_files = alphanumeric_sorting(history_files)
            sorted_coor_files = alphanumeric_sorting(coor_files)
            sorted_vel_files = alphanumeric_sorting(vel_files)
            sorted_xsc_files = alphanumeric_sorting(xsc_files)
            print "CHECK 3"
            #print sorted_history_files

            # sanity check
            i_run_history = sorted_history_files[1]
            i_run_history = i_run_history[:-8]
            i_run_history = i_run_history[-2:]

            i_run_coor = sorted_coor_files[1]
            i_run_coor = i_run_coor[:-13]
            i_run_coor = i_run_coor[-2:]

            i_run_vel = sorted_vel_files[1]
            i_run_vel = i_run_vel[:-12]
            i_run_vel = i_run_vel[-2:]

            i_run_xsc = sorted_xsc_files[1]
            i_run_xsc = i_run_xsc[:-12]
            i_run_xsc = i_run_xsc[-2:]

            if (i_run_coor == i_run_vel == i_run_xsc):
                print 'Restart files are from the same i_run: all good!'
                print i_run_coor
                print i_run_vel
                print i_run_xsc
            else:
                print 'Warning: restart files are NOT from the same i_run'
                print i_run_coor
                print i_run_vel
                print i_run_xsc

            if (i_run_history == i_run_coor):
                print 'History file and restart files are from the same i_run: all good!' 
                print i_run_history
                print i_run_coor
            else:
                print 'Warning: history file is NOT from the same i_run as restart files'  
                print i_run_history
                print i_run_coor

            path_to_replica_folder = os.getcwd()

            #######################################
            # getting stopped_i_run
            print "CHECK 4"
            hist_name = sorted_history_files[1]
            hist_name = hist_name[:-8]

            i_run_list = []
            for char in reversed(hist_name):
                if char.isdigit():
                    i_run_list.append(char)
                else:
                    break

            print "CHECK 5"
            reversed_i_run_list = []
            for i in reversed(i_run_list):
                reversed_i_run_list.append( str(i) )

            # sanity check
            print reversed_i_run_list

            stopped_i_run = ''
            for item in reversed_i_run_list:
                stopped_i_run = stopped_i_run + item
            #######################################    
            print "CHECK 6"
            print sorted_history_files[1]
            print os.getcwd()
            ff = open(sorted_history_files[1])
            lines = ff.readlines()
            ff.close()
            print "CHECK 7"
            data = lines[0].split()

            print "this is final data"
            print data
        except:
            pass
        os.chdir("../")
 
    os.chdir(home_dir)

    # populating replica_data list 
    replica_data.append(float(data[0]))
    replica_data.append(float(data[1]))
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
    # we use name of history file generated during first i_run in order to find 
    # replica directory and latest restart files
    history_name = base_name + "_" + replica_id + "_" + replica_cycle + "_10.history"
    replica_data = get_historical_data( history_name )
    print "one historical call returns...."

    # Q: why replica_temp is not used anywhere? is this normal?
    replica_temp = replica_data[0]
    replica_energy = replica_data[1]
    path_to_replica_folder = replica_data[2]
    stopped_i_run = replica_data[3]

    # getting history data for all replicas
    temperatures = [0.0]*replicas
    energies = [0.0]*replicas
    for j in range(replicas):
        history_name = base_name + "_" + str(j) + "_" + replica_cycle + "_10.history" 
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

