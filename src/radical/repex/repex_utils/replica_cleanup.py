"""
.. module:: radical.repex.repex_utils.replica_cleanup
.. moduleauthor::  <antons.treikalis@gmail.com>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"


import os
import sys
import shutil

#-------------------------------------------------------------------------------

def move_output_files(work_dir_local):
    """Moves all files generated and/or transferred from the remote HPC cluster
    during th simulation to simulation_output directory.

    Args:
        work_dir_local - path to current working direcgtory of the simulation

    Returns:
        None
    """
    
    dir_path = "{0}/simulation_output".format(work_dir_local)
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
        except: 
            raise

    pairs_name = "pairs_for_exchange_"
    obj_name   = "simulation_objects_"
    files = os.listdir( work_dir_local )

    for item in files:
        if (item.startswith(pairs_name) or item.startswith(obj_name) or item.endswith(".log") or item.endswith(".prof") or item.endswith(".mdout") or item.endswith(".mdinfo") ):
            source =  work_dir_local + "/" + str(item)
            destination = dir_path + "/"
            d_file = destination + str(item)
            if os.path.exists(d_file):
                os.remove(d_file)
            shutil.move( source, destination)

