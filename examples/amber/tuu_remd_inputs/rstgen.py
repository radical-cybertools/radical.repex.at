#!/usr/bin/python

"""
simple script for generating umbrella sampling restraint files
user need to provide a template file
assuming harmonic restraint (r2=r3), place holder is @val@
assume 1D for now, will implement 2D later
"""

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", help="name of the template restraint file")
parser.add_argument("-i", "--init", help="starting value of r2(r3)", type=float)
parser.add_argument("-s", "--spacing", help="spacing between umbrellas", type=float)
parser.add_argument("-n", "--number", help="number of umbrellas", type=int)
args = parser.parse_args()

r_file = open(args.file, "r")
tbuffer = r_file.read()
r_file.close()

for i in range(args.number):
    w_file = open(args.file+"."+str(i+1), "w")
    wbuffer = tbuffer.replace("@val@", str(args.init+i*args.spacing))
    w_file.write(wbuffer)
    w_file.close()



