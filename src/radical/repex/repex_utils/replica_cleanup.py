"""
.. module:: radical.repex.replica_cleanup
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"


import os
import sys
import shutil
from replicas.replica import Replica

#-------------------------------------------------------------------------------

def move_output_files(work_dir_local, re_pattern, replicas):
    """Moves all files, which were generated during the simulation 
    to replica directories. 

    """

    base = re_pattern.inp_basename + ".mdin"

    for r in range(len(replicas)):
        dir_path = "%s/replica_%d" % (work_dir_local, r )
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
            except: 
                raise

        files = os.listdir( work_dir_local )
        base_name =  base[:-5] + "_%s_" % replicas[r].id
        # moving matrix_column files
        col_name = "matrix_column" + "_%s_" % replicas[r].id
        for item in files:
            if (item.startswith(base_name) or item.startswith(col_name)):
                source =  work_dir_local + "/" + str(item)
                destination = dir_path + "/"
                shutil.move( source, destination)

#-------------------------------------------------------------------------------

def clean_up(work_dir_local, replicas):
    """Automates deletion of directories of individual replicas and all files in 
    those directories after the simulation.   

    Arguments:
    replicas - list of Replica objects
    """
    for r in range(len(replicas)):
        dir_path = "%s/replica_%d" % ( work_dir_local, replicas[r].id )
        shutil.rmtree(dir_path)
