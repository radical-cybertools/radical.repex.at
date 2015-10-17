"""
.. module:: radical.repex.replica_cleanup
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"


import os
import sys
import shutil

#-----------------------------------------------------------------------------------------------------------------------------------

def move_output_files(work_dir_local, inp_basename, replicas):
    """Moves all files starting with <inp_basename> to replica directories. These are files generated and 
    transferred to home dorectory as a result of NAMD simulation. This includes .coor, .xcs and other files.
    In addition to that files representing columns of swap matrix (<matrix_column_x.dat>) are transferred as well.

    Arguments:
    replicas - list of Replica objects
    """

    #----------------------------------------------------------
    # moving shared files
    #----------------------------------------------------------
    dir_path = "%s/shared_files" % (work_dir_local)
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
        except: 
            raise

    pairs_name = "pairs_for_exchange_"
    files = os.listdir( work_dir_local )

    for item in files:
        if (item.startswith(pairs_name)):
            source =  work_dir_local + "/" + str(item)
            destination = dir_path + "/"
            shutil.move( source, destination)

    #----------------------------------------------------------
    # moving individual files
    #----------------------------------------------------------

    for r in range(len(replicas)):
        dir_path = "%s/replica_%d" % (work_dir_local, r )
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
            except: 
                raise

        files = os.listdir( work_dir_local )

        base_name =  inp_basename[:-5] + "_%s_" % replicas[r].id
        col_name = "matrix_column" + "_%s_" % replicas[r].id
        rst_name = "ala10_us.RST." + "%s" % replicas[r].id

        for item in files:
            if (item.startswith(base_name) or item.startswith(col_name) or item.startswith(rst_name)):
                source =  work_dir_local + "/" + str(item)
                destination = dir_path + "/"
                shutil.move( source, destination)

#-----------------------------------------------------------------------------------------------------------------------------------

def clean_up(work_dir_local, replicas):
    """Automates deletion of directories of individual replicas and all files in 
    those directories after the simulation.   

    Arguments:
    replicas - list of Replica objects
    """
    for r in range(len(replicas)):
        dir_path = "%s/replica_%d" % ( work_dir_local, replicas[r].id )
        shutil.rmtree(dir_path)

    dir_path = "%s/shared_files" % ( work_dir_local )
    shutil.rmtree(dir_path)
