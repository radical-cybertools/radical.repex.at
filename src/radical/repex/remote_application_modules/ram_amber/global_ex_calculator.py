"""
.. module:: radical.repex.remote_application_modules.ram_amber.global_ex_calculator
.. moduleauthor::  <antons.treikalis@gmail.com>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import math
import json
import time
import random

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

    Args:
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
        #j = random.randint(0,(len(replicas)-1))
        return r_i  #don't exchange if this error occurred
    # actual replica
    r_j = replicas[j]

    return r_j

#-------------------------------------------------------------------------------
#
def do_exchange(replicas, swap_matrix):
    """Determines exchange pairs in current group of replicas. For each replica 
    we try to find an exchange partner by calling gibbs_exchange().

    Args:
        replicas - list of replica objects (replicas in same group)

        swap_matrix - matrix with reduced energies

    Returns:
        exchanged_pairs - list with pairs of replicas
    """

    exchanged_pairs = []
    for r_i in replicas:
        r_j = gibbs_exchange(r_i, replicas, swap_matrix)
        if r_j.id != r_i.id:
            exchanged_pairs.append( [r_i.id, r_j.id] )
    return  exchanged_pairs


#-------------------------------------------------------------------------------
#
class Replica(object):
    """Holds data associated with a given replica.
    """

    def __init__(self, 
                 my_id, 
                 d1_param=0.0, 
                 d2_param=0.0, 
                 d3_param=0.0, 
                 d1_type = None, 
                 d2_type = None, 
                 d3_type = None, 
                 new_restraints=None):   

        self.id = int(my_id)
        self.sid = int(my_id)

        self.d1_param = d1_param
        self.d2_param = d2_param
        self.d3_param = d3_param

        self.d1_type = d1_type
        self.d2_type = d2_type
        self.d3_type = d3_type

        if new_restraints is None:
            self.new_restraints = ''
        else:
            self.new_restraints = new_restraints
        self.potential_1 = 0

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    """Should be used only for salt concentration exchange. generates 
    pairs_for_exchange_d_c.dat file with pairs of replica id's. Replica pairs 
    specified in this file must exchange parameters.
    We first read from staging_area matrix_column.dat files to compose a 
    swap_matrix. Then for each replica we create a replica object to hold
    data associated with that replica. Next we call do_exchange() for replicas
    belonging to the same group and finaly we arite obtaned pairs of replicas to
    pairs_for_exchange_d_c.dat file. 
    """

    json_data = sys.argv[1]
    data=json.loads(json_data)

    replicas      = int(data["replicas"])
    cycle         = int(data["cycle"])
    current_cycle = int(data["current_cycle"])
    dimension     = int(data["dimension"])
    group_nr      = int(data["group_nr"])
    dim_string    = data["dim_string"]
    group_size    = replicas / group_nr
    groups        = data["group_ids"]

    replica_ids = list()
    for g in groups:
        for i in g:
            replica_ids.append(int(i))

    print "replica_ids: "
    print replica_ids
    
    dim_types = []
    dim_types.append('')
    dim_types += dim_string.split()

    nr_dims = int(len( dim_string.split() ))

    replica_dict = {}
    replicas_obj = []

    umbrella = False
    for d_type in dim_types:
        if d_type == 'umbrella':
            umbrella = True

    base_name = "matrix_column"
    swap_matrix = [[ 0. for j in range(replicas)] for i in range(replicas)]

    for r_id in replica_ids:
        success = 0
        attempts = 0
        column_file = base_name + "_" + str(r_id) + "_" + str(cycle) + ".dat" 
        path = "../staging_area/" + column_file     
        while (success == 0):
            try:
                f = open(path)
                lines = f.readlines()
                f.close()
                # populating matrix column
                data = lines[0].split()
                for i in range(replicas):
                    swap_matrix[i][int(r_id)] = float(data[i])
                # populating replica dict
                data = lines[1].split()
                replica_dict[data[0]] = [data[1], data[2], data[3], data[4]]
                # updating rstr_val's for a given replica
                rid = data[0]
   
                if (umbrella == True):
                    current_rstr = replica_dict[rid][1]
                    try:
                        r_file = open(("../staging_area/" + current_rstr), "r")
                    except IOError:
                        print "Warning: unable to access template file: {0}".format(current_rstr)

                    tbuffer = r_file.read()
                    r_file.close()
                    tbuffer = tbuffer.split()

                    line = 2
                    rstr_val_2 = -1.0
                    rstr_vals = []
                    for word in tbuffer:
                        if word == '/':
                            line = 3
                        if word.startswith("r2=") and line == 2:
                            num_list = word.split('=')
                            rstr_val_1 = float(num_list[1])
                            rstr_vals.append( rstr_val_1 )
                        if word.startswith("r2=") and line == 3:
                            num_list = word.split('=')
                            rstr_val_2 = float(num_list[1])
                            rstr_vals.append( rstr_val_2 )

                params = [0.0]*4
                for i,j in enumerate(dim_types):
                    if dim_types[i] == 'temperature':
                        params[i] = replica_dict[rid][2]
                    elif dim_types[i] == 'umbrella':
                        params[i] = rstr_vals.pop(0)
                    elif dim_types[i] == 'salt':
                        params[i] = replica_dict[rid][3]

                if nr_dims == 3:
                    r = Replica(rid, 
                                d1_param = params[1], 
                                d2_param = params[2], 
                                d3_param = params[3], 
                                d1_type = dim_types[1], 
                                d2_type = dim_types[2], 
                                d3_type = dim_types[3], 
                                new_restraints=replica_dict[rid][1])
                elif nr_dims == 2:
                    r = Replica(rid, 
                                d1_param = params[1], 
                                d2_param = params[2], 
                                d1_type = dim_types[1], 
                                d2_type = dim_types[2], 
                                new_restraints=replica_dict[rid][1])
                elif nr_dims == 1:
                    r = Replica(rid, 
                                d1_param = params[1], 
                                d1_type = dim_types[1], 
                                new_restraints=replica_dict[rid][1])

                replicas_obj.append(r)
                success = 1
                print "Success processing replica: %s" % r_id
            except:
                print "Waiting for replica: %s" % r_id
                time.sleep(1)
                attempts += 1
                if attempts > 10:
                    print "Can't access matrix columns for replica: %s" % r_id
                    success = 1
                pass

    #---------------------------------------------------------------------------

    d1_list = []
    d2_list = []
    d3_list = []
    exchange_list = []

    if nr_dims == 3:
        for r1 in replicas_obj:   
            if dimension == 1:
                r_pair = [r1.d2_param, r1.d3_param]
                if r_pair not in d1_list:
                    d1_list.append(r_pair)
                    current_group = []
                    for r2 in replicas_obj:
                        if (r1.d2_param == r2.d2_param) and (r1.d3_param == r2.d3_param):
                            current_group.append(r2)
                    exchange_pairs = do_exchange(current_group, swap_matrix)
                    exchange_list += exchange_pairs

            elif dimension == 2:
                r_pair = [r1.d1_param, r1.d3_param]
                if r_pair not in d2_list:
                    d2_list.append(r_pair)
                    current_group = []
                    for r2 in replicas_obj:
                        if (r1.d1_param == r2.d1_param) and (r1.d3_param == r2.d3_param):
                            current_group.append(r2)
                    exchange_pairs = do_exchange(current_group, swap_matrix)
                    exchange_list += exchange_pairs

            elif dimension == 3:
                r_pair = [r1.d1_param, r1.d2_param]
                if r_pair not in d3_list:
                    d3_list.append(r_pair)
                    current_group = []
                    for r2 in replicas_obj:
                        if (r1.d1_param == r2.d1_param) and (r1.d2_param == r2.d2_param):
                            current_group.append(r2)
                    exchange_pairs = do_exchange(current_group, swap_matrix)
                    exchange_list += exchange_pairs
    elif nr_dims == 2:
        for r1 in replicas_obj:
            if dimension == 1:
                r_par = r1.d2_param
                if r_par not in d1_list:
                    d1_list.append(r_par)
                    current_group = []
                    for r2 in replicas_obj:
                        if (r1.d2_param == r2.d2_param):
                            current_group.append(r2)
                    exchange_pairs = do_exchange(current_group, swap_matrix)
                    exchange_list += exchange_pairs

            elif dimension == 2:
                r_par = r1.d1_param
                if r_par not in d2_list:
                    d2_list.append(r_par)
                    current_group = []
                    for r2 in replicas_obj:
                        if (r1.d1_param == r2.d1_param):
                            current_group.append(r2)
                    exchange_pairs = do_exchange(current_group, swap_matrix)
                    exchange_list += exchange_pairs
    elif nr_dims == 1:
        for r_i in replicas_obj:
            r_j = gibbs_exchange(r_i, replicas_obj, swap_matrix)
            if (r_j != r_i):
                exchange_pair = []
                exchange_pair.append(r_i.id)
                exchange_pair.append(r_j.id)
                exchange_list.append(exchange_pair)

    #---------------------------------------------------------------------------
    # writing to file

    try:
        outfile = "pairs_for_exchange_{dim}_{cycle}.dat".format(dim=dimension, cycle=current_cycle)
        with open(outfile, 'w+') as f:
            for pair in exchange_list:
                if pair:
                    row_str = str(pair[0]) + " " + str(pair[1]) 
                    f.write(row_str)
                    f.write('\n')
            pwd = os.getcwd()
            f.write(pwd)
            f.write('\n')
        f.close()

    except IOError:
        print 'Error: unable to create column file %s for replica %s' % (outfile, replica_id)

