"""
.. module:: radical.repex.namd_kernels.launch_simulation
.. moduleauthor::  <antons.treikalis@gmail.com>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import time
import math
import datetime

def read_mdinfo(name):
    """Reads simulation speend and simulation execuiton time (in secs) from
    Amber's .mdinfo files generated durig simulation

    Args:
        name - name of the .mdinfo file
    """

    try:
        r_file = open(name, "r")
    except IOError:
        print 'Warning: unable to access file: {0}'.format( name )

    try:
        line_buffer = r_file.readlines()
        r_file.close()
    except:
        print "error opening file"
        raise

    sim_speed = 0.0
    exec_time = 0.0
    for line in line_buffer:
        row = line.split()

        if (len(row) == 7) and (row[1] == 'ns/day'):
            if float(row[3]) > sim_speed:
                sim_speed = float(row[3])

        if (len(row) == 8) and (row[1] == 'Elapsed(s)'):
            if float(row[3]) > exec_time:
                exec_time = float(row[3])

    return sim_speed, exec_time

#-------------------------------------------------------------------------------

if __name__ == "__main__":
    """This module should be called in location where all .mdinfo files 
    generated durig simulation are located. Usually this is on remote HPC custer
    in RP's sandbox. Prints the ttal number of .mdinfo files, avegare simulation 
    speed, total execution time in seconds and average execuiton time in 
    seconds. Note: all measurements are done by Amber!
    """
    
    sim_list = []
    exec_list = []
    count = 0.0

    root = os.getcwd()
    for path, subdirs, files in os.walk(root):
        for name in files:
            f = os.path.join(path, name)
            if f.endswith('.mdinfo'):
    	        count += 1.0
                sim, exect = read_mdinfo(f)
                sim_list.append(sim)
                exec_list.append(exect)
    
    total_sim_speed = 0.0
    for t in sim_list:
    	total_sim_speed += t
    avg_sim = total_sim_speed / count

    total_exec_time = 0.0
    for i in exec_list:
        total_exec_time += i
    avg_exec_time = total_exec_time / count

    try:        
        with open("all-exec-times.dat", 'w+') as f:
            for item in exec_list:
                f.write(str(item))
                f.write('\n')
            f.close()
    except:
        raise

    print "count:           {0}".format( count )
    print "avg sim speed:   {0} ns/day".format( avg_sim )
    print "total_exec_time: {0} secs".format( total_exec_time )
    print "avg_exec_time:   {0} secs".format( avg_exec_time )

