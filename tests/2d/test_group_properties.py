import os
import pytest
import json
import radical.utils.logger as rul
from os import path

import radical.utils.logger as rul
import pilot_kernels
from pilot_kernels.pilot_kernel_pattern_s_multi_d_sc import PilotKernelPatternSmultiDsc
from pilot_kernels.pilot_kernel_pattern_s_multi_d_scg import PilotKernelPatternSmultiDscg

from amber_kernel.kernel_pattern_s import KernelPatternS

@pytest.fixture(scope="class")
def repex_file_setup(fname):
    work_dir_local = (os.getcwd()+"/inputs")
    with open("inputs/%s"%fname) as data_file:
        inp_file = json.load(data_file)

    with open("inputs/stampede.json") as config_file:
        rconfig = json.load(config_file)

    
    return inp_file, rconfig, work_dir_local

@pytest.fixture(scope="class")
def replica_num(fname):
    with open("inputs/%s"%fname) as data_file:
        inp_file = json.load(data_file)

    d1 = int(inp_file["dim.input"]["d1"]["number_of_replicas"])
    d2 = int(inp_file["dim.input"]["d2"]["number_of_replicas"])
#    d3 = int(inp_file["dim.input"]["d3"]["number_of_replicas"])

    return d1,d2

@pytest.fixture(scope="class")
def max_replica(d1,d2):
    temp = []
    temp.append(d1)
    temp.append(d2)
#    temp.append(d3)
    print temp
    temp = sorted(temp)
    print temp
    return temp[1]
    
@pytest.fixture(scope="class")
def repex_initialize(fname):
    inp_file, rconfig, work_dir_local = repex_file_setup(fname)
    n = inp_file["dim.input"]["d1"]["number_of_replicas"]
    md_kernel    = KernelPatternS( inp_file, rconfig, work_dir_local )
    a = md_kernel.initialize_replicas()
    return md_kernel, a    

@pytest.fixture(scope="class")
def repex_initialize_shared_data():
    inp_file, rconfig, work_dir_local = repex_file_setup(fname)
    n = inp_file["dim.input"]["d1"]["number_of_replicas"]
    md_kernel    = KernelPatternS( inp_file, rconfig, work_dir_local )
    a = md_kernel.initialize_replicas()
    md_kernel.prepare_shared_data(a)
    return md_kernel,a    


class Test_replica_tests(object):
    def test_initialize_replica_id(self,cmdopt):
        fname = cmdopt
        md_kernel, a = repex_initialize(fname)
	d1,d2 = replica_num(fname)

	test_out = range(d1*d2)
	replica_output = []
	for i in range(0,len(a)):
            replica_output.append(a[i].id)
	    #print a[i].group_idx

	print replica_output
	print test_out
	assert sorted(replica_output) == sorted(test_out)

    def test_total_group(self,cmdopt):
        fname = cmdopt
        md_kernel, a = repex_initialize(fname)
        replica_output = []
        for i in range(0,len(a)):
            replica_output.append(a[i].group_idx)

        d1,d2 = replica_num(fname)
        max1 = max_replica(d1,d2)
        print max1
        assert max(max(replica_output))+1 == (max1)

class Test_groups(object):
    def test_group_d1(self,cmdopt):
        fname = cmdopt
        md_kernel, a = repex_initialize(fname)
        d1,d2 = replica_num(fname)
        temp = [[] for x in xrange(d2)]
        test_out = []
        #test_out = [2,2,2,2]
        for i in range(d2):
            test_out.append(d1)
        print test_out
        i=0
        
        if i < d2:
            for x in temp:
                for r in a:
                    print 'r.group_idx',r.group_idx[0], 'i',i
                    if (r.group_idx[0]==i):
                        x.append(r)
                i = i+1
        
        num_out = []
        for x in temp:
            num_out.append(len(x))
        print num_out
        print cmdopt
        assert num_out == test_out    


    def test_group_d2(self,cmdopt):
        fname = cmdopt
        md_kernel, a = repex_initialize(fname)
        d1,d2 = replica_num(fname)
        temp = [[] for x in xrange(d1)]
        test_out = []
        #test_out = [2,2,2,2]
        for i in range(d1):
            test_out.append(d2)
        #print test_out
        i=0
        
        if i < d1:
            for x in temp:
                for r in a:
                    print 'r.group_idx',r.group_idx[1], 'i',i
                    if (r.group_idx[1]==i):
                        x.append(r)
                i = i+1
        print 'temp',temp
        print 'len', len(temp[0])
        num_out = []
        for x in temp:
            num_out.append(len(x))
        print num_out
        assert num_out == test_out


class Testbasic(object):
    def test_import(self):
	from amber_kernel.kernel_pattern_s import KernelPatternS

    #def test_try(self,cmdopt):
    #    fname = cmdopt
        #from amber_kernel.kernel_pattern_s import KernelPatternS
    #    inp_file, rconfig, work_dir_local = repex_file_setup(fname)
        #print cmdopt
    #    assert inp_file['remd.input'].get('group_exec') == 'False'


    def test_name(self,cmdopt):
        fname = cmdopt
    	from amber_kernel.kernel_pattern_s import KernelPatternS
        md_kernel, a = repex_initialize(fname)
        print md_kernel.name
        assert md_kernel.name == 'amber-pattern-s-3d'
