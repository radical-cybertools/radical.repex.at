"""
.. module:: radical.repex.md_kernles.amber_kernels_us.global_ex_calculator
.. moduleauthor::  <antons.treikalis@rutgers.edu>
.. moduleauthor::  <haoyuan.chen@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import math
import json
import time
import shutil
import random
from mpi4py import MPI

#-------------------------------------------------------------------------------

def bond(c1,c2):

    r = 0.0
    for i in range(3):
        r += (float(c1[i])-float(c2[i]))**2
    return math.sqrt(r)

def angle(c1,c2,c3):

    r = 0.0; n1 = 0.0; n2 = 0.0
    for i in range(3):
        r += (float(c1[i])-float(c2[i]))*(float(c3[i])-float(c2[i]))
        n1 += (float(c1[i])-float(c2[i]))**2
        n2 += (float(c3[i])-float(c2[i]))**2
    r = r/math.sqrt(n1)/math.sqrt(n2)
    return math.acos(r)*180.0/math.pi

def dihedral(c1,c2,c3,c4):

    #this piece of code needs to be improved later
    v21 = []; v32 = []; v43 = []; n_n1 = 0.0; n_n2 = 0.0; r = 0.0; dih = 0.0; det = 0.0
    for i in range(3):
        v21.append(float(c2[i])-float(c1[i])); v32.append(float(c3[i])-float(c2[i])); v43.append(float(c4[i])-float(c3[i]))
    n1 = [v21[1]*v32[2]-v21[2]*v32[1], v21[2]*v32[0]-v21[0]*v32[2], v21[0]*v32[1]-v21[1]*v32[0]]
    n2 = [v32[1]*v43[2]-v32[2]*v43[1], v32[2]*v43[0]-v32[0]*v43[2], v32[0]*v43[1]-v32[1]*v43[0]]
    for i in range(3):
        n_n1 += n1[i]**2; n_n2 += n2[i]**2
    n_n1 = math.sqrt(n_n1); n_n2 = math.sqrt(n_n2)
    for i in range(3):
        n1[i] = n1[i]/n_n1; n2[i] = n2[i]/n_n2
    for i in range(3):
        r += n1[i]*n2[i]
    dih = math.acos(r)*180.0/math.pi
    for i in range(3):
        det += n1[i]*v43[i]
    if det >= 0.0: return dih
    else: return 360.0-dih

class Restraint(object):

    def __init__(self):

        self.crd_file = ''
        self.rstr_entry = ''
        self.crd_data = []
        self.rstr_type = ''
        self.rstr_atoms = []
        self.rstr_atoms_crds = []
        self.energy = 0.0

    def set_crd(self, crd_file):

        self.crd_data = []
        self.crd_file = crd_file
        try:
            crd = file(self.crd_file,'r')
            self.crd_data = crd.readlines()
            crd.close()
        except:
            try:
                time.sleep(1)
                crd = file(self.crd_file,'r')
                self.crd_data = crd.readlines()
                crd.close()
            except:
                print "File %s is not found." % self.crd_file

    def set_rstr(self, rstr_entry):

        self.rstr_type = ''
        self.rstr_atoms = []
        self.rstr_atoms_crds = []
        self.rstr_entry = rstr_entry
        #ugly hack...trying to be more general
        self.rstr_atoms = self.rstr_entry.split('iat')[1].split('r')[0].replace('=',' ').replace(',',' ').strip().split()
        if len(self.rstr_atoms) == 2: self.rstr_type = 'BOND'
        elif len(self.rstr_atoms) == 3: self.rstr_type = 'ANGLE'
        elif len(self.rstr_atoms) == 4:
            if 'rstwt' in self.rstr_entry: self.rstr_type = 'GENCRD'
            else: self.rstr_type = 'DIHEDRAL'
        for atom in self.rstr_atoms:
            if int(atom) % 2: self.rstr_atoms_crds.append(self.crd_data[int(atom)/2+2][:36].split())
            else: self.rstr_atoms_crds.append(self.crd_data[int(atom)/2+1][37:].strip().split())

    def calc_energy(self):

        self.r = 0.0
        if self.rstr_type == 'BOND': self.r = bond(self.rstr_atoms_crds[0],self.rstr_atoms_crds[1])
        elif self.rstr_type == 'ANGLE': self.r = angle(self.rstr_atoms_crds[0],self.rstr_atoms_crds[1],self.rstr_atoms_crds[2])
        elif self.rstr_type == 'DIHEDRAL': self.r = dihedral(self.rstr_atoms_crds[0],self.rstr_atoms_crds[1],self.rstr_atoms_crds[2],self.rstr_atoms_crds[3])
        elif self.rstr_type == 'GENCRD':
            gc1 = bond(self.rstr_atoms_crds[0],self.rstr_atoms_crds[1]); gc2 = bond(self.rstr_atoms_crds[2],self.rstr_atoms_crds[3])
            w1 = float(self.rstr_entry.split('rstwt')[1].replace('=',' ').replace(',',' ').replace('/',' ').replace('&end',' ').strip().split()[0])
            w2 = float(self.rstr_entry.split('rstwt')[1].replace('=',' ').replace(',',' ').replace('/',' ').replace('&end',' ').strip().split()[1])
            self.r = w1*gc1 + w2*gc2

        r1 = float(self.rstr_entry.split('r1')[1].split('r2')[0].replace('=','').replace(',','').strip())
        r2 = float(self.rstr_entry.split('r2')[1].split('r3')[0].replace('=','').replace(',','').strip())
        r3 = float(self.rstr_entry.split('r3')[1].split('r4')[0].replace('=','').replace(',','').strip())
        r4 = float(self.rstr_entry.split('r4')[1].split('rk2')[0].replace('=','').replace(',','').strip())
        rk2 = float(self.rstr_entry.split('rk2')[1].split('rk3')[0].replace('=','').replace(',','').strip())
        rk3 = float(self.rstr_entry.split('rk3')[1].split('rstwt')[0].replace('=','').replace(',','').replace('/',' ').replace('&end',' ').strip())

        if (self.rstr_type == 'ANGLE') or (self.rstr_type == 'DIHEDRAL'):
            rk2 = rk2 / (180.0/math.pi) / (180.0/math.pi)
            rk3 = rk3 / (180.0/math.pi) / (180.0/math.pi)

        #see page 414 in amber 14 manual
        if self.r < r1: self.energy = rk2*(r1-r2)**2 - 2.0*rk2*(r1-r2)*(self.r-r1)
        elif (self.r >= r1) and (self.r < r2): self.energy = rk2*(self.r-r2)**2
        elif (self.r >= r2) and (self.r <= r3): self.energy = 0.0
        elif (self.r > r3) and (self.r <= r4): self.energy = rk3*(self.r-r3)**2
        elif self.r > r4: self.energy = rk3*(r4-r3)**2 - 2.0*rk3*(r4-r3)*(self.r-r4)

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

#-------------------------------------------------------------------------------

def get_historical_data(replica_path=None, history_name=None):
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

    ACTUALLY WE ONLY NEED THE POTENTIAL FROM HERE. TEMPERATURE GOTTA BE OBTAINED FROM THE PROPERTY OF THE REPLICA OBJECT.
    """

    home_dir = os.getcwd()
    if replica_path != None:
        path = "../staging_area" + replica_path
        os.chdir(path)

    temp = 0.0    #temperature
    eptot = 0.0   #potential
    try:
        f = open(history_name)
        lines = f.readlines()
        f.close()
        path_to_replica_folder = os.getcwd()
        for i in range(len(lines)):
            if "EAMBER (non-restraint)" in lines[i]:   #this is the real potential energy without restraints!
                eptot = float(lines[i].strip().split()[-1])
    except:
        os.chdir(home_dir)
        raise
        
    #if replica_path != None:
    #    os.chdir("../")
    #    os.chdir(home_dir)

    os.chdir(home_dir)

    return eptot, path_to_replica_folder

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
    swap_matrix - matrix of dimension-less energies, where each column is a replica 
    and each row is a state

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
def do_exchange(dimension, replicas, swap_matrix):
    """
    """

    exchanged = []
    for r_i in replicas:
        # does this pick a correct one????
        r_j = gibbs_exchange(r_i, replicas, swap_matrix)
       
        if (r_j.id != r_i.id) and (r_j.id not in exchanged) and (r_i.id not in exchanged):
            exchanged.append(r_j.id)
            exchanged.append(r_i.id)
            
    return  exchanged

#-------------------------------------------------------------------------------
#
class Replica(object):
    """Class representing replica and it's associated data.
    """
    def __init__(self, my_id):
       
        self.id = int(my_id)
        self.sid = int(my_id)

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    """
    """

    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    json_data = sys.argv[1]
    data=json.loads(json_data)

    current_cycle = int(data["current_cycle"])
    replicas = int(data["replicas"])
    base_name = data["base_name"]

    all_temperatures = data["all_temperatures"]
    all_restraints = data["all_restraints"]

    comm.Barrier()

    #---------------------------------------------------------------------------    
    # assigning replicas to procs
    if rank == 0:
        r_ids = []
        num = replicas / size
        if replicas % size == 0:
            for p in range(size):
                r_ids.append([])
                for r in range(replicas):
                    if p == r:
                        for i in range(num):
                            r_ids[p].append(r+size*i)

    else:
        r_ids = None

    r_ids = comm.bcast(r_ids, root=0)
    #---------------------------------------------------------------------------    
    pwd = os.getcwd()

    # init swap column
    swap_column = [0.0]*replicas
    temperatures = [0.0]*replicas
    energies = [0.0]*replicas
    all_energies = [0.0]*replicas

    comm.Barrier()

    #---------------------------------------------------------------------------
    id_number = 0
    for replica_id in r_ids[rank]:
        str_rid = str(replica_id)
        #temperatures = [0.0]*replicas
        #energies = [0.0]*replicas

        # getting history data for self
        history_name = base_name + "_" + \
                       str(replica_id) + "_" + \
                       str(current_cycle) + ".mdinfo"
        success = 0
        attempts = 0
        while (success == 0):
            try:
                replica_path = "/replica_%d/" % (replica_id)
                replica_energy, path_to_replica_folder = get_historical_data(replica_path, history_name)
                
                success1 = 0        
                current_rstr = all_restraints[str_rid]
                while (success1 == 0):
                    try:
                        #-------------------------------------------------------
                        # can avoid this step!
                        rstr_ppath = "../staging_area/" + current_rstr
                        rstr_file = file(rstr_ppath,'r')
                        rstr_lines = rstr_file.readlines()
                        rstr_file.close()
                        #-------------------------------------------------------
                        rstr_entries = ''.join(rstr_lines).split('&rst')[1:]
                        us_energy = 0.0
                        r = Restraint()

                        new_coor = "%s_%d_%d.rst" % (base_name, replica_id, current_cycle)
                        new_coor_path = "../staging_area" + replica_path + new_coor

                        r.set_crd(new_coor_path)
                        for rstr_entry in rstr_entries:
                            r.set_rstr(rstr_entry); r.calc_energy()
                            us_energy += r.energy
                        energies[replica_id] = replica_energy + us_energy

                        success1 = 1
                        print "Success processing replica: %s" % str_rid
                    except:
                        print "Waiting for replica: %s" % str_rid
                        time.sleep(1)
                        pass

                print "rank: {0} temp: {1} energy: {2}".format(rank, all_temperatures[str_rid], (replica_energy + us_energy) )
                energies     = comm.gather((replica_energy + us_energy), root=0)

                if rank == 0:  
                    for r in range(size):
                        index = r_ids[r][id_number]
                        #print "index: %d" % index
                        all_energies[index] = energies[r] 

                print "rank {0}: Got history data for self!".format(rank)
                success = 1
                id_number += 1
            except:
                print "rank {0}: Waiting for self (history file)".format(rank)
                time.sleep(1)
                attempts += 1
                if attempts >= 3:
                    print "rank {0}: Amber run failed, matrix_swap_column_x_x.dat populated with zeros".format(rank)

                    #-----------------------------------------------------------
                    # temp fix
                    replica_temp = 0.0
                    replica_energy = 0.0
                    temperatures = comm.gather(replica_temp, root=0)
                    energies     = comm.gather(replica_energy, root=0)
                    #-----------------------------------------------------------
 
                    success = 1
                pass

    all_energies = comm.bcast(all_energies, root=0)

    #---------------------------------------------------------------------------
    if rank ==0:
        swap_matrix = []
        temp_columns = [[0.0]*replicas]*replicas

    for replica_id in r_ids[rank]:
        swap_column = [0.0]*replicas
        for j in range(replicas):
            # check if this is correct!!!!!! (indexes...)
            swap_column[j] = reduced_energy(float(all_temperatures[str(j)]), all_energies[replica_id])

        temp_columns = comm.gather(swap_column, root=0)

        if rank == 0:
            for col in temp_columns:
                swap_matrix.append(col)

    if rank == 0:
        replica_dict = {}
        replicas_obj = []
        for rid in range(replicas):
            str_rid = str(rid)
            try:
                current_rstr = all_restraints[str_rid]
                try:
                    r_file = open(("../staging_area/" + current_rstr), "r")
                except IOError:
                    print "Warning: unable to access restraints file: {0}".format(current_rstr)

                tbuffer = r_file.read()
                r_file.close()
                tbuffer = tbuffer.split()

                # contents of rts file
                # umbrella sampling restraints on phi/psi torsions
                #  &rst iat=49,55,57,59 r1=30.0 r2=120.0 r3=120.0 r4=210.0 rk2=100 rk3=100 /

                line = 2
                for word in tbuffer:
                    if word.startswith("r2=") and line == 2:
                        num_list = word.split('=')
                        rstr_val_1 = float(num_list[1])
                    
                # creating replica
                r = Replica(rid)
                replicas_obj.append(r)

                success = 1
                print "Success processing replica: %s" % rid

            except:
                print "Waiting for replica restraint file: %s" % rid
                time.sleep(1)
                pass

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

        