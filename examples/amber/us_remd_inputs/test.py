import os
import sys
import math
import json
import time
import random

if __name__ == '__main__':

    try:
        rstr_ppath = "ace_ala_nme_double.RST"
        rstr_file = file(rstr_ppath,'r')
        rstr_lines = rstr_file.readlines()
        rstr_file.close()
        #---------------------------------------------------------------
        rstr_entries = ''.join(rstr_lines).split('&rst')[1:]
        us_energy = 0.0
        
        print "rstr_entries: "
        print rstr_entries
        #r = Restraint()
        #r.set_crd(new_coor)
        #for rstr_entry in rstr_entries:
        #    r.set_rstr(rstr_entry); r.calc_energy()
        #    us_energy += r.energy
        
        
    except:
        rase
