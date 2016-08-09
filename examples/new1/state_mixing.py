#!/usr/bin/python

"""
generate state-mixing profile (for U dimension in TSU)
"""

import sys,argparse,copy

def swap(my_array,pair):
    i = pair[0]
    j = pair[1]
    t = my_array[i]
    my_array[i] = my_array[j]
    my_array[j] = t

def read_pairs(filename):
    f = file(filename,'r')
    d = f.readlines()
    f.close()
    pairs = []
    for l in d[:-1]:
        p = map(int,l.strip().split())
        pairs.append(p)
    return pairs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-nr", "--number_of_replicas", help="total number of replicas", type=int)
    parser.add_argument("-ns", "--number_of_states", help="number of states in this dimension", type=int)
    parser.add_argument("-fs", "--pairs_for_exchange_files", help="comma-separated, ordered list of names of the pairs_for_exchange files")
    args = parser.parse_args()
    nr = args.number_of_replicas
    ns = args.number_of_states
    fs = args.pairs_for_exchange_files.split(",")
    state_matrix = []
    my_array = range(nr)
    for f in fs:
        current_array = copy.deepcopy(my_array)
        state_matrix.append(current_array)
        pairs = read_pairs(f)
        for p in pairs:
            swap(my_array,p)
    f = file("state_mixing.dat",'w')
    for i in range(nr):
        for j in range(len(fs)):
            line = str(int(state_matrix[j][i])%ns) + "\n"
            f.write(line)
        f.write("\n")
    f.close()

main()
