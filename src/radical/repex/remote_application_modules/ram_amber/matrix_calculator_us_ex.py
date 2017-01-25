"""
.. module:: radical.repex.remote_application_modules.ram_amber.matrix_calculator_us_ex
.. moduleauthor::  <antons.treikalis@gmail.com>
.. moduleauthor::  <haoyuan.chen@rutgers.edu>
"""

__copyright__ = "Copyright 2013-2014, http://radical.rutgers.edu"
__license__ = "MIT"

import os
import sys
import json
import math
import time
import fcntl
import shutil

#-------------------------------------------------------------------------------

def bond(c1,c2):
    """
    """

    r = 0.0
    for i in range(3):
        r += (float(c1[i])-float(c2[i]))**2
    return math.sqrt(r)

def angle(c1,c2,c3):
    """
    """

    r = 0.0; n1 = 0.0; n2 = 0.0
    for i in range(3):
        r += (float(c1[i])-float(c2[i]))*(float(c3[i])-float(c2[i]))
        n1 += (float(c1[i])-float(c2[i]))**2
        n2 += (float(c3[i])-float(c2[i]))**2
    r = r/math.sqrt(n1)/math.sqrt(n2)
    return math.acos(r)*180.0/math.pi

def dihedral(c1,c2,c3,c4):
    """
    """

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

def calc(r,r1,r2,r3,r4,rk2,rk3):
    """
    """

    #see page 414 in amber 14 manual
    energy = 0.0
    if r < r1: energy = rk2*(r1-r2)**2 - 2.0*rk2*(r1-r2)*(r-r1)
    elif (r >= r1) and (r < r2): energy = rk2*(r-r2)**2
    elif (r >= r2) and (r <= r3): energy = 0.0
    elif (r > r3) and (r <= r4): energy = rk3*(r-r3)**2
    elif r > r4: energy = rk3*(r4-r3)**2 - 2.0*rk3*(r4-r3)*(r-r4)
    return energy

class Replica(object):
    """Represents replica object and it's associated data for umbrella exchange.

    Attributes:
        crd_file - name of coordinates file

        rstr_entry - string with parameters from restraint file (we may have 
        multiple such strings)

        crd_data - data read from coordinates file

        rstr_type - string representing restraint type

        rstr_atoms - list with atoms obtained from restraint file

        rstr_atoms_crds - list with atoms obtained from coordinates file

        energy - energy of this replica
    """

    def __init__(self):

        self.crd_file = ''
        self.rstr_entry = ''
        self.crd_data = []
        self.rstr_type = ''
        self.rstr_atoms = []
        self.rstr_atoms_crds = []
        self.energy = 0.0

    def set_crd(self, crd_file):
        """reads data from coordinates file and assigns that data to crd_data
        atribute

        Args:
            crd_file - name of coordinates file
        """

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
        """sets rstr_atoms, rstr_type and rstr_atoms_crds attributes  

        Args:
            rstr_entry - string with parameters from restraint file (we may have 
        multiple such strings)
        """

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
        """sets energy attribute
        
        """

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

        if self.rstr_type == 'DIHEDRAL':
            #assuming r2=r3, which is normally this case
            if abs(self.r-360.0-r2) < abs(self.r-r2):
                self.r -= 360.0
            elif abs(self.r+360.0-r2) < abs(self.r-r2):
                self.r += 360.0

        self.energy = calc(self.r,r1,r2,r3,r4,rk2,rk3)

#-------------------------------------------------------------------------------

def get_historical_data(replica_path=None, history_name=None):
    """reads potential energy from a given .mdinfo file

    Args:
        replica_path - path to replica directory in RP's staging_area

        history_name - name of .mdinfo file

    Returns:
        eptot - potential energy
    """

    home_dir = os.getcwd()
    if replica_path is not None:
        path = "../staging_area" + replica_path
        os.chdir(path)

    temp = 0.0    #temperature
    eptot = 0.0   #potential
    try:
        f = open(history_name)
        lines = f.readlines()
        f.close()
        for i,j in enumerate(lines):
            if "EAMBER (non-restraint)" in lines[i]:   
                #this is the real potential energy without restraints!
                eptot = float(lines[i].strip().split()[-1])
    except:
        raise
        
    if replica_path is not None:
        os.chdir("../")
        os.chdir(home_dir)

    return eptot

#-------------------------------------------------------------------------------

if __name__ == '__main__':
    """This RAM is executed after Amber call to obtain data needed to populate 
    a column of a swap matrix for this replica.

    For this replica we read .mdinfo file and obtain energy values.
    For all replicas which are in the same group with this replica we 
    read .RST files.
    Finally, we write all necessary data to history_info_us.dat file, which
    is located in staging_area of this pilot.

    Note: there is only a single instance of history_info_us.dat file and 
    each CU associated with some replica is writing to this file (we use locks).
    Then, CU responsible for exchange calculations reads from that file.
    """

    json_data = sys.argv[1]
    data=json.loads(json_data)

    replica_id = int(data["rid"])
    replica_cycle = int(data["replica_cycle"])
    replicas = int(data["replicas"])
    base_name = data["base_name"]
    new_restraints = data["new_restraints"]

    prmtop_name = data["amber_parameters"]
    mdin_name = data["amber_input"]

    init_temp = float(data["init_temp"])
    rstr_vals = data["rstr_vals"]

    print "temp_par: {0}".format(init_temp)

    print "rstr_vals: "
    print rstr_vals

    current_group_rst = data["current_group_rst"]

    print "current_group_rst: "
    print current_group_rst
   
    # FILE ala10_remd_X_X.rst IS IN DIRECTORY WHERE THIS SCRIPT IS LAUNCHED AND 
    # CAN BE REFERRED TO AS:
    new_coor = "%s_%d_%d.rst" % (base_name, replica_id, replica_cycle)

    # getting history data for self
    history_name = base_name + "_" + str(replica_id) + "_" + str(replica_cycle) + ".mdinfo"
    replica_path = "/replica_%d/" % (replica_id)

    swap_column = [0.0]*replicas

    success  = 0
    attempts = 0
    while (success == 0):
        try:
            replica_energy = get_historical_data(replica_path=None, history_name=history_name)
            print "Got history data for self!"
            success = 1
        except:
            print "Waiting for self (history file)"
            time.sleep(1)
            attempts += 1
            if attempts > 10:
                replica_energy = -1.0
                print "MD run failed for replica {0}".format(replica_id)
            pass

    us_energies = [0.0]*replicas

    #---------------------------------------------------------------------------
    # performance consideration: 
    # if we write all restraint info (during cycle 1 by replica 0) to a single
    # file and copy this file to staging_area, will it be faster to
    # read this file by each replica vs. reading N individual restraint
    # files?
    # keep in mind: in 1D each replica read N files, but in 3D it only
    # reads math.pow(N, 1/3) files
    #---------------------------------------------------------------------------
    for j in current_group_rst.keys():
        success  = 0     
        attempts = 0   
        current_rstr = current_group_rst[j]
        while (success == 0):
            try: 
                rstr_ppath = "../staging_area/" + current_rstr
                rstr_file = file(rstr_ppath,'r')
                rstr_lines = rstr_file.readlines()
                rstr_file.close()
                rstr_entries = ''.join(rstr_lines).split('&rst')[1:]
                us_energy = 0.0
                r = Replica()
                r.set_crd(new_coor)
                for rstr_entry in rstr_entries:
                    r.set_rstr(rstr_entry)
                    r.calc_energy()
                    us_energy += r.energy
                us_energies[int(j)] = us_energy
                success = 1
                print "Success calculating us_energy for replica: {0}".format(j)
            except:
                print "Waiting to get .RST to calculate us_energy for replica: {0}".format(j)
                time.sleep(1)
                attempts += 1
                if attempts > 5:
                    us_energies[int(j)] = -1.0
                    print "Replica {0} failed, setting us_energies[{0}] to -1.0".format(j)
                    success = 1
                pass

    print "us_energies: "
    print us_energies

    history_str = str(replica_id) + " " + \
                  str(init_temp) + " " + \
                  str(replica_energy) + " " + \
                  str(new_restraints) + " "

    for val in rstr_vals:
        history_str += str(val) + " "

    for e in us_energies:
        history_str += str(e) + " "
    history_str += "\n"

    print "history_str: {0}".format(history_str)
 
    pwd = os.getcwd()
    size = len(pwd)-1
    path = pwd
    for i in range(0,size):
        if pwd[size-i] != '/':
            path = path[:-1]
        else:
            break

    path += "staging_area/history_info_us.dat" 
    try:
        with open(path, "a") as g:
            fcntl.flock(g, fcntl.LOCK_EX)
            g.write(history_str)
            fcntl.flock(g, fcntl.LOCK_UN)
    except:
        raise

    