
__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import math
import json
import time
import random
from mpi4py import MPI

#-------------------------------------------------------------------------------
#
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

#-------------------------------------------------------------------------------
#
def get_historical_data(replica_path, history_name):
    """Retrieves temperature and potential energy from simulation output file 
    .history file.
    This file is generated after each simulation run. The function searches for 
    directory 
    where .history file recides by checking all computeUnit directories on 
    target resource.

    Arguments:
    history_name - name of .history file for a given replica. 

    Returns:
    data[0] - temperature obtained from .history file
    data[1] - potential energy obtained from .history file
    path_to_replica_folder - path to computeUnit directory on a target resource 
    where all
    input/output files for a given replica recide.
       Get temperature and potential energy from mdinfo file.
    """

    home_dir = os.getcwd()
    if replica_path != None:
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
        path_to_replica_folder = os.getcwd()
        for i in range(len(lines)):
            if "TEMP(K)" in lines[i]:
                temp = float(lines[i].split()[8])
            elif "EPtot" in lines[i]:
                eptot = float(lines[i].split()[8])
    except:
        os.chdir(home_dir)
        raise 

    os.chdir(home_dir)
    
    return temp, eptot, path_to_replica_folder

#-------------------------------------------------------------------------------
#
def weighted_choice_sub(weights):
    """Adopted from asyncre-bigjob [1]
    """

    rnd = random.random() * sum(weights)
    for i, w in enumerate(weights):
        rnd -= w
        if rnd < 0:
            return i

#-------------------------------------------------------------------------------
#
def gibbs_exchange(r_i, replicas, swap_matrix):
    """Adopted from asyncre-bigjob [1]
    Produces a replica "j" to exchange with the given replica "i"
    based off independence sampling of the discrete distribution

    Arguments:
    r_i - given replica for which is found partner replica
    replicas - list of Replica objects
    swap_matrix - matrix of dimension-less energies, where each column is a 
    replica and each row is a state

    Returns:
    r_j - replica to exchnage parameters with
    """

    #evaluate all i-j swap probabilities
    ps = [0.0]*(len(replicas))

    j = 0
    for r_j in replicas:
        ps[j] = -(swap_matrix[r_i.sid][r_j.id] + swap_matrix[r_j.sid][r_i.id] - 
                  swap_matrix[r_i.sid][r_i.id] - swap_matrix[r_j.sid][r_j.id]) 
        j += 1
        
    ######################################
    new_ps = []
    for item in ps:
        if item > math.log(sys.float_info.max): new_item=sys.float_info.max
        elif item < math.log(sys.float_info.min) : new_item=0.0
        else :
            new_item = math.exp(item)
        new_ps.append(new_item)
    ps = new_ps
    # index of swap replica within replicas_waiting list
    j = len(replicas)
    while j > (len(replicas) - 1):
        j = weighted_choice_sub(ps)
        
    # guard for errors
    if j is None:
        j = random.randint(0,(len(replicas)-1))
        print "...gibbs exchnage warning: j was None..."
    # actual replica
    r_j = replicas[j]
    ######################################

    return r_j

#-------------------------------------------------------------------------------
#
class Replica(object):
    """Class representing replica and it's associated data.
    """
    def __init__(self, my_id, new_temperature=None):
       
        self.id = int(my_id)
        self.sid = int(my_id)

        if new_temperature is None:
            self.new_temperature = 0
        else:
            self.new_temperature = new_temperature

#-------------------------------------------------------------------------------
#
if __name__ == '__main__':
    """
    """

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    argument_list = str(sys.argv)
    current_cycle = int(sys.argv[1])
    replicas = int(sys.argv[2])
    base_name = str(sys.argv[3])

    comm.Barrier()

    # replica id equals to rank
    replica_id = rank

    # getting history data for self
    history_name = base_name + "_" + \
                   str(replica_id) + "_" + \
                   str(current_cycle) + ".mdinfo"

    # init swap column
    swap_column = [0.0]*replicas

    #---------------------------------------------------------------------------

    success = 0
    attempts = 0
    while (success == 0):
        try:
            replica_path = "/"
            replica_temp, replica_energy, path_to_replica_folder = get_historical_data(replica_path, history_name)
            print "rank {0}: Got history data for self!".format(rank)
            success = 1
        except:
            print "rank {0}: Waiting for self (history file)".format(rank)
            time.sleep(1)
            attempts += 1
            if attempts >= 12:
                print "rank {0}: Amber run failed, matrix_swap_column_x_x.dat populated with zeros".format(rank)
            pass

    #---------------------------------------------------------------------------
    temperatures = [0.0]*replicas
    energies = [0.0]*replicas

    comm.Barrier()
    
    #all_temperatures = comm.gather(temperatures, all_temperatures, root=0)
    temperatures = comm.allgather(replica_temp)
    energies = comm.allgather(replica_energy)

    #---------------------------------------------------------------------------
    # init swap column
    swap_column = [0.0]*replicas

    for j in range(replicas):      
        swap_column[j] = reduced_energy(temperatures[j], replica_energy)

    #---------------------------------------------------------------------------
    # part of global calc
    
    if rank == 0:
        swap_matrix = [[ 0. for j in range(replicas)] for i in range(replicas)]

    swap_matrix = comm.gather(swap_column, root=0)

    if rank == 0:
        replicas_obj = []
        for rid in range(replicas):
            # creating replica with dummy temperature, since it is not needed
            r = Replica(int(rid), new_temperature=0.0)
            replicas_obj.append(r)

        #-----------------------------------------------------------------------

        exchange_list = []
        for r_i in replicas_obj:
            r_j = gibbs_exchange(r_i, replicas_obj, swap_matrix)
            if (r_j != r_i):
                exchange_pair = []
                exchange_pair.append(r_i.id)
                exchange_pair.append(r_j.id)
                exchange_list.append(exchange_pair)
            
        #-----------------------------------------------------------------------
        # writing to file

        try:
            outfile = "pairs_for_exchange_{cycle}.dat".format(cycle=current_cycle)
            with open(outfile, 'w+') as f:
                for pair in exchange_list:
                    if pair:
                        row_str = str(pair[0]) + " " + str(pair[1]) 
                        f.write(row_str)
                        f.write('\n')
            f.close()

        except IOError:
            print 'Error: unable to create column file %s for replica %s' % \
            (outfile, replica_id)
    
