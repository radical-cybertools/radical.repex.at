#!/usr/bin/python

"""
calculate the (apparent) acceptance ratio in one exchange step
"""

import sys,argparse

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

def compare(array1,array2):
    count = 0
    for i in range(len(array1)):
        if array1[i] != array2[i]:
            count += 1
    return count

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--number_of_replicas", help="total number of replicas", type=int)
    parser.add_argument("-f", "--filename", help="name of the pairs_for_exchange file")
    args = parser.parse_args()
    pairs = read_pairs(args.filename)
    my_array = range(args.number_of_replicas)
    for p in pairs:
        swap(my_array,p)
    count = compare(my_array,range(args.number_of_replicas))
    print "Acceptance Ratio = %6.4f" %(float(count)/args.number_of_replicas)

main()
