"""
.. module:: radical.repex.replica_cleanup
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"


import os
import sys
import shutil

#-------------------------------------------------------------------------------

def move_output_files(work_dir_local, md_kernel, replicas):

    #---------------------------------------------------------------------------
    # moving shared files

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
            d_file = destination + str(item)
            if os.path.exists(d_file):
                os.remove(d_file)
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

    dir_path = "%s/shared_files" % ( work_dir_local )
    shutil.rmtree(dir_path)
