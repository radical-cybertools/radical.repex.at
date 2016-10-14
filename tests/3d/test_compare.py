import os
import sys
import json
import pickle
import glob
from os import path
import radical.utils.logger as rul
from repex_utils.replica_cleanup import *
from repex_utils.parser import parse_command_line

from pilot_kernels.pilot_kernel_pattern_s_multi_d_sc  import PilotKernelPatternSmultiDsc
from pilot_kernels.pilot_kernel_pattern_s_multi_d_scg import PilotKernelPatternSmultiDscg
from pilot_kernels.pilot_kernel_pattern_a_multi_d     import PilotKernelPatternAmultiD

from amber_kernel.kernel_pattern_s import KernelPatternS


class Test_sim_result(object):
    def _init_(self):
        self.dic_d1={}
        self.dic_d2={}
        self.dic_d3={}
        self.inp_file = None
        self.rconfig = None
        self.work_dir_local = None
        self.replicas = None
        self.pilot_kernel = None
        self.md_kernel = None
        self.no_cycle = None
        
    def repex_file_setup(self,fname):
        self.work_dir_local = (os.getcwd()+"/inputs")
        with open("inputs/%s"%fname) as data_file:
            self.inp_file = json.load(data_file)

        with open("inputs/stampede.json") as config_file:
            self.rconfig = json.load(config_file)
        #return inp_file, rconfig, work_dir_local

    def repex_initialize(self):   
        n = self.inp_file["dim.input"]["d1"]["number_of_replicas"]
        self.no_cycle = int(self.inp_file["remd.input"]["number_of_cycles"])
        self.md_kernel    = KernelPatternS( self.inp_file, self.rconfig, self.work_dir_local )
        self.pilot_kernel = PilotKernelPatternSmultiDsc( self.inp_file, self.rconfig )
        self.replicas = self.md_kernel.initialize_replicas()
        #return md_kernel  

    def run_simulation(self):
        
	try:
            self.pilot_kernel.launch_pilot()
		# now we can run RE simulation
	    self.pilot_kernel.run_simulation( self.replicas, self.md_kernel )
	    move_output_files(work_dir_local, md_kernel, replicas )
	except (KeyboardInterrupt, SystemExit) as e:
            print "Exit requested..."
            #self.pilot_kernel.session.close (cleanup=True, terminate=True)
	    sys.exit(1)
	except:
	    print "Unexpected error: {0}".format(sys.exc_info()[0])
	    #self.pilot_kernel.session.close (cleanup=True, terminate=True)
	    #sys.exit(1)
        finally:
	    print "Closing session."
	    self.pilot_kernel.session.close (cleanup=True, terminate=True)

        #return pilot_kernel
    
    def read_file(self, filename,dim):
        f = file(filename,'r')
        d = f.readlines()
        f.close()
        dic = {}
        for l in d[:-1]:
            p = map(int,l.strip().split())
            #print p
            self.swap(p,dim)


    def add_to_dict(self):
        self.repex_initialize()
        dic_d1={}
        dic_d2={}
        dic_d3={}
	for i in range(0,len(self.replicas)):
            #print i
            dic_d1[i]=self.replicas[i].dims['d1']['par']
            dic_d2[i]=self.replicas[i].dims['d2']['par']
            dic_d3[i]=self.replicas[i].dims['d3']['par']
            #print self.replicas[i].id,dic_d1[i],dic_d2[i],dic_d3[i]
	    #print self.replicas[i].id, 'param:',self.replicas[i].dims['d1']['par'],self.replicas[i].dims['d2']['par'],self.replicas[i].dims['d3']['par']
        self.dic_d1 = dic_d1
        self.dic_d2 = dic_d2
        self.dic_d3 = dic_d3
        print 'before swap',self.dic_d2
        #return md_kernel
        
    
    def swap(self,p,dim):
        if dim == 1:
            temp = self.dic_d1[p[0]]
            self.dic_d1[p[0]] = self.dic_d1[p[1]]
            self.dic_d1[p[1]] = temp

        if dim == 2:
            temp = self.dic_d2[p[0]]
            self.dic_d2[p[0]] = self.dic_d2[p[1]]
            self.dic_d2[p[1]] = temp

        if dim == 3:
            temp = self.dic_d3[p[0]]
            self.dic_d3[p[0]] = self.dic_d3[p[1]]
            self.dic_d3[p[1]] = temp

    def recover_replicas(self,inpfile):

        replicas = []
        with open(inpfile, 'rb') as input:
            for i in range(0,len(self.replicas)):
                r_temp = pickle.load(input)
                replicas.append( r_temp )
        return replicas

def test_simulation(cmdopt):
    classobj = Test_sim_result()
    #fname = cmdopt
    fname = 'sync/tuu_remd_ace_ala_nme.json'
    classobj.repex_file_setup(fname)
    classobj.add_to_dict()

    classobj.run_simulation()
    
    for cycle in range (1, classobj.no_cycle+1):
        for dim in range(1, 4):
            classobj.read_file("pairs_for_exchange_{0}_{1}.dat".format(dim,cycle),dim)
            print 'pair file:', "pairs_for_exchange_{0}_{1}.dat".format(dim,cycle)
            if dim == 1:
                print 'after swap:',classobj.dic_d1
            elif dim ==2:
                print 'after swap:',classobj.dic_d2
            else:
                print 'after swap:',classobj.dic_d3
                
            dic_d1={}
            replicas = classobj.recover_replicas("simulation_objects_{0}_{1}.pkl".format(dim,cycle))
            print 'pkl file:',"simulation_objects_{0}_{1}.pkl".format(dim,cycle)
            #dim = dim+1
            #cycle = cycle+1
            for i in range(0,len(replicas)):
                #print i
                dic_d1[i]=replicas[i].dims['d{0}'.format(dim)]['par']
                #print a[i].id, 'param:',a[i].dims['d1']['par'],a[i].dims['d2'],a[i].dims['d3']
            print 'pkl        ',dic_d1
            if dim == 1:
                print 'inside assert 1'
                assert classobj.dic_d1==dic_d1
            elif dim ==2:
                print 'assert 2'
                assert classobj.dic_d2==dic_d1
            else:
                print 'assert 3'
                assert classobj.dic_d3==dic_d1
            files = glob.glob('*')
    for f in files:
        if "pairs_for_exchange" in f:
            os.remove(f)
        if "simulation_objects" in f:
            os.remove(f)
            
##    classobj.read_file("/home/suvigya/repex_june21/radical.repex/repex-test/pairs_for_exchange_3_1.dat",3)
##    print 'after swap:',classobj.dic_d3
##    dic_d1={}
##    replicas = classobj.recover_replicas("/home/suvigya/repex_june21/radical.repex/repex-test/simulation_objects_3_1.pkl")
##    #print 'len:',len(replicas)
##    for i in range(0,len(replicas)):
##        #print i
##        dic_d1[i]=replicas[i].dims['d3']['par']
##        #print a[i].id, 'param:',a[i].dims['d1']['par'],a[i].dims['d2'],a[i].dims['d3']
##    print 'pkl        ',dic_d1
##    assert classobj.dic_d3==dic_d1
