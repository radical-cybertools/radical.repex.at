
__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"


import os
import sys
import json
import math
import time
import shutil
from mpi4py import MPI
from subprocess import *
import subprocess

#-------------------------------------------------------------------------------

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

def get_historical_data(replica_path, history_name):
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

if __name__ == '__main__':

    json_data = sys.argv[1]
    data=json.loads(json_data)

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()
    
    rids = data["ex"].keys()
    rid = rids[rank]

    group_id = data["gen_input"]["group_id"]
    amber_input = data["gen_input"]["substr"] + data["gen_input"]["amber_inp"]
    cycle_steps = data["gen_input"]["steps"]
    new_restraints = data["gen_input"]["substr"] + data["ex"][rid]["new_rstr"]
    new_temperature = data["ex"][rid]["new_t"]
    basename = data["gen_input"]["base"]
    cycle = data["gen_input"]["cnr"]
    us_template = data["gen_input"]["substr"] + data["gen_input"]["us_tmpl"]
    rstr_val_1 = float(data["ex"][rid]["rv1"])
    rstr_val_2 = float(data["ex"][rid]["rv2"])
    replica_coor = data["ex"][rid]["r_coor"]

    amber_path = data['amber']['path']

    new_input_file = "%s_%s_%s.mdin" % (basename, rid, cycle)
    output_file = "%s_%s_%s.mdout" % (basename, rid, cycle)
    amber_parameters = data["gen_input"]["substr"] + data["gen_input"]["amber_prm"]
    coor_file = data["gen_input"]["substr"] + data["ex_temp"][rid]["r_coor"]
    new_coor = "%s_%s_%s.rst" % (basename, rid, cycle)
    new_traj = "%s_%s_%s.mdcrd" % (basename, rid, cycle)
    new_info = "%s_%s_%s.mdinfo" % (basename, rid, cycle)
    old_coor = "%s_%s_%d.rst" % (basename, rid, (int(cycle)-1))

    replicas = int(data["gen_input"]["replicas"])

    #---------------------------------------------------------------------------
    # build input file
    try:
        r_file = open(amber_input, "r")
    except IOError:
        print "Warning: unable to access template file: {0}".format(amber_input) 

    tbuffer = r_file.read()
    r_file.close()

    tbuffer = tbuffer.replace("@nstlim@",cycle_steps)
    tbuffer = tbuffer.replace("@disang@",new_restraints)
    tbuffer = tbuffer.replace("@temp@",new_temperature)

    if cycle == '0':
        tbuffer = tbuffer.replace("@irest@","0")
        tbuffer = tbuffer.replace("@ntx@","1")
    else:
        tbuffer = tbuffer.replace("@irest@","1")
        tbuffer = tbuffer.replace("@ntx@","5")

    try:
        w_file = open(new_input_file, "w")
        w_file.write(tbuffer)
        w_file.close()
    except IOError:
        print "Warning: unable to access file: {0}".format(new_input_file)
 
    #---------------------------------------------------------------------------
    # MD:

    if cycle == '0':
        argument_str = " -O " + " -i " + new_input_file + " -o " + output_file + \
                       " -p " +  amber_parameters + " -c " + coor_file + \
                       " -r " + new_coor + " -x " + new_traj + " -inf " + new_info 
    else:
        argument_str = " -O " + " -i " + new_input_file + " -o " + output_file + \
                       " -p " +  amber_parameters + " -c " + old_coor + \
                       " -r " + new_coor + " -x " + new_traj + " -inf " + new_info

    cmd = amber_path + argument_str
    process = Popen(cmd, subprocess.PIPE, shell=True)
    process.wait()

    #---------------------------------------------------------------------------
    # good up to here
    # Exchange:

    pwd = os.getcwd()
    matrix_col = "matrix_column_%s_%s.dat" % ( rid, cycle ) 
    swap_column = [0.0]*replicas

    #---------------------------------------------------------------------------
    success = 0
    attempts = 0
    while (success == 0):
        try:
            history_name = basename + "_" + rid + "_" + cycle + ".mdinfo"
            
            replica_temp, replica_energy, path_to_replica_folder = get_historical_data(None, history_name)
            print "Got history data for self!"
            success = 1
        except:
            print "Waiting for self (history file)"
            time.sleep(1)
            attempts += 1
            # most likely amber run failed, we write zeros to matrix column file
            if attempts >= 5:

                # writing to file
                try:
                    outfile = "matrix_column_{replica}_{cycle}.dat".format(cycle=replica_cycle, replica=replica_id )
                    with open(outfile, 'w+') as f:
                        row_str = ""
                        for item in swap_column:
                            if len(row_str) != 0:
                                row_str = row_str + " " + str(item)
                            else:
                                row_str = str(item)
                            f.write(row_str)
                            f.write('\n')
                            row_str = str(replica_id) + " " + str(cycle) + " " + new_restraints + " " + str(new_temperature)
                            f.write(row_str)

                        f.close()

                except IOError:
                    print 'Error: unable to create column file %s for replica %s' % (outfile, replica_id)
                #---------------------------------------------------------------------------------------------------
                sys.exit("Amber run failed, matrix_swap_column_x_x.dat populated with zeros")
            pass

    temperatures = [0.0]*replicas 
    energies = [0.0]*replicas

    m_temperatures = [0.0]*replicas 
    m_energies = [0.0]*replicas

    if rank == 0:
        temp_pairs = [[0, 0.0]]*size
        energy_pairs = [[0, 0.0]]*size

    temp_pairs  = comm.gather([int(rid), replica_temp], root=0)
    energy_pairs  = comm.gather([int(rid), replica_energy], root=0)

    if rank == 0:
        for pair in temp_pairs:
            m_temperatures[pair[0]] = pair[1]
        for pair in energy_pairs:
            m_energies[pair[0]] = pair[1]

    temperatures = comm.bcast(m_temperatures, root=0)
    energies = comm.bcast(m_energies, root=0)

    if rank ==0:
        matrix_columns = [[0.0]*(replicas+1)]*(replicas+1)
        data_list = [["","","",""]]*size

    data_col = [rid, cycle, new_restraints, new_temperature]

    for j in rids:
        swap_column[int(j)] = reduced_energy(float(temperatures[int(j)]), energies[int(rid)])

    # adding rid as a first element of swap column:
    swap_column.insert(0,int(rid))

    matrix_columns = comm.gather(swap_column, root=0)
    data_list = comm.gather(data_col, root=0)
   
    # we do a single write of all columns in current group to file
    # instead of a single column by each replica
    #---------------------------------------------------------------------------
    # writing to file
    if rank == 0:
        try:
            outfile = "matrix_column_{group}_{cycle}.dat".format(cycle=cycle, group=group_id )
            with open(outfile, 'w+') as f:
                for swap_column in matrix_columns:
                    row_str = ""
                    for item in swap_column:
                        if len(row_str) != 0:
                            row_str = row_str + " " + str(item)
                        else:
                            row_str = str(item)
                    f.write(row_str)
                    f.write('\n')
                for entry in data_list:
                    row_str = ""
                    for i in entry:
                        row_str += i + " "
                    f.write(row_str)
                    f.write('\n')
            f.close()

        except IOError:
            print 'Error: unable to create column file %s for replica %s' % (outfile, replica_id)

