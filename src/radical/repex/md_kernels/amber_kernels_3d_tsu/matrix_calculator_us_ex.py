"""
.. module:: radical.repex.md_kernels.amber_kernels_3d_tsu.matrix_calculator_us_ex
.. moduleauthor::  <haoyuan.chen@rutgers.edu>
.. moduleauthor::  <antons.treikalis@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import json
import math
import time

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

def get_historical_data(replica_path=None, history_name=None):
    """Retrieves temperature and potential energy from simulation output file 
    .history file. This file is generated after each simulation run. The 
    function searches for directory where .history file recides by checking all 
    computeUnit directories on target resource.

    Arguments:
    history_name - name of .history file for a given replica. 

    Returns:
    data[0] - temperature obtained from .history file
    data[1] - potential energy obtained from .history file
    path_to_replica_folder - path to computeUnit directory on a target resource 
    where all input/output files for a given replica recide.
       Get temperature and potential energy from mdinfo file.

    ACTUALLY WE ONLY NEED THE POTENTIAL FROM HERE. TEMPERATURE GOTTA BE OBTAINED 
    FROM THE PROPERTY OF THE REPLICA OBJECT.
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
        raise
        
    if replica_path != None:
        os.chdir("../")
        os.chdir(home_dir)

    return eptot, path_to_replica_folder

#-------------------------------------------------------------------------------
#
if __name__ == '__main__':
    """ TODO 
    """

    json_data = sys.argv[1]
    data=json.loads(json_data)

    replica_id = int(data["replica_id"])
    replica_cycle = int(data["replica_cycle"])
    replicas = int(data["replicas"])
    base_name = data["base_name"]
    new_restraints = data["new_restraints"]

    prmtop_name = data["amber_parameters"]
    mdin_name = data["amber_input"]
    init_temp = float(data["init_temp"])
    init_salt = float(data["init_salt"])

    current_group_rst = data["current_group_rst"]
   
    new_coor = "%s_%d_%d.rst" % (base_name, replica_id, replica_cycle)

    pwd = os.getcwd()
    matrix_col = "matrix_column_%d_%d.dat" % ( replica_id, replica_cycle ) 

    # getting history data for self
    history_name = base_name + "_" + str(replica_id) + "_" + str(replica_cycle) + ".mdinfo"
    replica_path = "/replica_%d/" % (replica_id)

    swap_column = [0.0]*replicas

    success = 0
    attempts = 0
    while (success == 0):
        try:
            replica_energy, path_to_replica_folder = get_historical_data(replica_path=None, history_name=history_name)
            print "Got history data for self!"
            success = 1
        except:
            print "Waiting for self (history file)"
            time.sleep(1)
            attempts += 1
            # most likely amber run failed
            # so we write zeros to matrix column file
            if attempts >= 12:
                #---------------------------------------------------------------
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
                            row_str = str(replica_id) + " " + str(replica_cycle) + " " + new_restraints + " " + str(init_temp) + " " + str(init_salt)
                            f.write(row_str)

                        f.close()

                except IOError:
                    print 'Error: unable to create column file %s for replica %s' % (outfile, replica_id)
                #---------------------------------------------------------------
                sys.exit("Amber run failed, matrix_swap_column_x_x.dat populated with zeros")
            pass

    # getting history data for all replicas
    # we rely on the fact that last cycle for every replica is the same, e.g. == replica_cycle
    # but this is easily changeble for arbitrary cycle numbers
    temperatures = [0.0]*replicas   #need to pass the replica temperature here
    energies = [0.0]*replicas

    #if replica_cycle != 0:
    for j in current_group_rst.keys():
        success = 0        
        current_rstr = current_group_rst[j]
        while (success == 0):
            try:
                #---------------------------------------------------------------
                # can avoid this step!
                rstr_ppath = "../staging_area/" + current_rstr
                rstr_file = file(rstr_ppath,'r')
                rstr_lines = rstr_file.readlines()
                rstr_file.close()
                #---------------------------------------------------------------
                rstr_entries = ''.join(rstr_lines).split('&rst')[1:]
                us_energy = 0.0
                r = Restraint()
                r.set_crd(new_coor)
                for rstr_entry in rstr_entries:
                    r.set_rstr(rstr_entry); r.calc_energy()
                    us_energy += r.energy
                energies[int(j)] = replica_energy + us_energy
                temperatures[int(j)] = float(init_temp)

                success = 1
                print "Success processing replica: %s" % j
            except:
                print "Waiting for replica: %s" % j
                time.sleep(1)
                pass

    #for j in range(replicas):
    for j in current_group_rst.keys():      
        swap_column[int(j)] = reduced_energy(temperatures[int(j)], energies[int(j)])

    #---------------------------------------------------------------------------
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
            row_str = str(replica_id) + " " + str(replica_cycle) + " " + new_restraints + " " + str(init_temp) + " " + str(init_salt)
            f.write(row_str)

        f.close()

    except IOError:
        print 'Error: unable to create column file %s for replica %s' % (outfile, replica_id)

