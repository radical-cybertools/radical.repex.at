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

LOCAL_HOME = "/home/suvigya"
work_dir = "repex-gen/radical.repex/bin"


@pytest.fixture(scope="class")
def repex_file_setup():  
    work_dir_local = (os.getcwd()+"/inputs")
    with open("inputs/tuu_remd_ace_ala_nme.json") as data_file:
        inp_file = json.load(data_file)

    with open("inputs/stampede.json") as config_file:
        rconfig = json.load(config_file)

    
    return inp_file, rconfig, work_dir_local

@pytest.fixture(scope="class")
def replica_num():
    with open("inputs/tuu_remd_ace_ala_nme.json") as data_file:
        inp_file = json.load(data_file)

    d1 = int(inp_file["dim.input"]["d1"]["number_of_replicas"])
    d2 = int(inp_file["dim.input"]["d2"]["number_of_replicas"])
    d3 = int(inp_file["dim.input"]["d3"]["number_of_replicas"])

    return d1,d2,d3

@pytest.fixture(scope="class")
def max_replica(d1,d2,d3):
    temp = []
    temp.append(d1)
    temp.append(d2)
    temp.append(d3)
    print temp
    temp = sorted(temp)
    print temp
    return temp[1],temp[2]
    
@pytest.fixture(scope="class")
def repex_initialize():
    inp_file, rconfig, work_dir_local = repex_file_setup()
    n = inp_file["dim.input"]["d1"]["number_of_replicas"]
    md_kernel    = KernelPatternS( inp_file, rconfig, work_dir_local )
    print md_kernel.work_dir_local
    print md_kernel.input_folder
    print md_kernel.amber_coordinates_path
    a = md_kernel.initialize_replicas()
    return md_kernel, a    

@pytest.fixture(scope="class")
def repex_initialize_shared_data():
    inp_file, rconfig, work_dir_local = repex_file_setup()
    n = inp_file["dim.input"]["d1"]["number_of_replicas"]
    md_kernel    = KernelPatternS( inp_file, rconfig, work_dir_local )
    a = md_kernel.initialize_replicas()
    md_kernel.prepare_shared_data(a)
    return md_kernel,a    
    
@pytest.fixture(scope="class")
def repex_initialize_e2e():
    inp_file, rconfig, work_dir_local = repex_file_setup()
    #n = inp_file["dim.input"]["d1"]["number_of_replicas"]
    md_kernel    = KernelPatternS( inp_file, rconfig, work_dir_local )
    pilot_kernel = PilotKernelPatternSmultiDsc( inp_file, rconfig )
    return md_kernel, pilot_kernel , work_dir   

#######################################################################################################
class Testbasic(object):
    def test_try(self):
        inp_file, rconfig, work_dir_local = repex_file_setup()
        assert inp_file['remd.input'].get('group_exec') == 'False'


    def test_name(self):
        md_kernel, a = repex_initialize()
        assert md_kernel.name == 'samber-pattern-s-3d'


class Test_replica_tests(object):
    def test_initialize_replica_id(self):
        md_kernel, a = repex_initialize()
        d1,d2,d3 = replica_num()

        test_out = range(d1*d2*d3)
        replica_output = []
        for i in range(0,len(a)):
            replica_output.append(a[i].id)
            print a[i].group_idx

        print replica_output
        print test_out
        assert sorted(replica_output) == sorted(test_out)

##    def test_initialize_replica_group_idx(self):
##        md_kernel, a = repex_initialize()
##        test_out = [[0, 0, 0],
##                    [1, 1, 0],
##                    [2, 0, 1],
##                    [3, 1, 1],
##                    [0, 2, 2],
##                    [1, 3, 2],
##                    [2, 2, 3],
##                    [3, 3, 3]]
##        replica_output = []
##        for i in range(0,len(a)):
##            replica_output.append(a[i].group_idx)
##            print  a[i].group_idx 
##            #print a[i].dims['d1']
##        
##        #print 'max',max(max(replica_output))
##        assert sorted(replica_output) == sorted(test_out)


    def test_total_group(self):
        md_kernel, a = repex_initialize()
        replica_output = []
        for i in range(0,len(a)):
            replica_output.append(a[i].group_idx)

        d1,d2,d3 = replica_num()
        max1,max2 = max_replica(d1,d2,d3)
        print max1*max2
        assert max(max(replica_output))+1 == (max1*max2)


##################################################################################################
        
class Test_groups(object):
    def test_group_d1(self):
        md_kernel, a = repex_initialize()
        d1,d2,d3 = replica_num()
        temp = [[] for x in xrange(d2*d3)]
        test_out = []
        #test_out = [2,2,2,2]
        for i in range(d2*d3):
            test_out.append(d1)
        print test_out
        i=0
        
        if i < d2*d3:
            for x in temp:
                for r in a:
                    if (r.group_idx[0]==i):
                        x.append(r)
                i = i+1
        
        num_out = []
        for x in temp:
            num_out.append(len(x))
        print num_out
        assert num_out == test_out


    def test_group_d2(self):
        md_kernel, a = repex_initialize()
        d1,d2,d3 = replica_num()
        temp = [[] for x in xrange(d1*d3)]
        test_out = []
        #test_out = [2,2,2,2]
        for i in range(d1*d3):
            test_out.append(d2)
        print test_out
        i=0
        
        if i < d1*d3:
            for x in temp:
                for r in a:
                    if (r.group_idx[1]==i):
                        x.append(r)
                i = i+1
        
        num_out = []
        for x in temp:
            num_out.append(len(x))
        print num_out
        assert num_out == test_out


    def test_group_d3(self):
        md_kernel, a = repex_initialize()
        d1,d2,d3 = replica_num()
        temp = [[] for x in xrange(d1*d2)]
        test_out = []
        #test_out = [2,2,2,2]
        for i in range(d1*d2):
            test_out.append(d3)
        print test_out
        i=0
        
        if i < d1*d2:
            for x in temp:
                for r in a:
                    if (r.group_idx[2]==i):
                        x.append(r)
                i = i+1
        
        num_out = []
        for x in temp:
            num_out.append(len(x))
        print num_out
        assert num_out == test_out
############################################################################################

# class Test_E2E(object):
#     def test_endtoend(self):
#         md_kernel,pilot_kernel,work_dir = repex_initialize_e2e()
#         replicas = md_kernel.initialize_replicas()
#         try:
#             pilot_manager, pilot_object, session = pilot_kernel.launch_pilot()
#             pilot_kernel.run_simulation( replicas, pilot_object, session, md_kernel )
#         except:
# 	    raise
#         try:
#             # finally we are moving all files to individual replica directories
#             move_output_files(work_dir_local, md_kernel, replicas ) 
    
#             logger.info("Simulation successfully finished!")
# 	    logger.info("Please check output files in replica_x directories.")
# 	except:
# 	    logger.info("Unexpected error: {0}".format(sys.exc_info()[0]) )
# 	    raise 
# 	finally :
# 	    logger.info("Closing session.")
# 	    session.close (cleanup=True, terminate=True)  

############################################################################################
##        
##class Test_d1(object):
##    def test_d1_d1_par(self):
##        md_kernel, a = repex_initialize()
##        temp1 = []
##        temp2 = []
##        temp3 = []
##        temp4 = []
##        test_out = [[0,360],[0,360],[0,360],[0,360]]
##        for r in a:
##            if(r.group_idx[0]==0):
##                temp1.append(r.dims['d1']['par'])
##
##            if(r.group_idx[0]==1):
##                temp2.append(r.dims['d1']['par'])
##
##            if(r.group_idx[0]==2):
##                temp3.append(r.dims['d1']['par'])
##
##            if(r.group_idx[0]==3):
##                temp4.append(r.dims['d1']['par'])
##
##        print temp1
##        print temp2
##        print temp3
##        print temp4
##        output = [temp1,temp2,temp3,temp4]
##        assert output == test_out
##        
##
##    def test_d1_d2_par(self):
##        md_kernel, a = repex_initialize()
##        temp1 = []
##        temp2 = []
##        temp3 = []
##        temp4 = []
##        test_out = [[300,300],[300,300],[600,600],[600,600]]
##        for r in a:
##            if(r.group_idx[0]==0):
##                temp1.append(r.dims['d2']['par'])
##
##            if(r.group_idx[0]==1):
##                temp2.append(r.dims['d2']['par'])
##
##            if(r.group_idx[0]==2):
##                temp3.append(r.dims['d2']['par'])
##
##            if(r.group_idx[0]==3):
##                temp4.append(r.dims['d2']['par'])
##        
##        print temp1
##        print temp2
##        print temp3
##        print temp4
##        output = [temp1,temp2,temp3,temp4]
##        assert output == test_out
##        
##
##    def test_d1_d3_par(self):
##        md_kernel, a = repex_initialize()
##        temp1 = []
##        temp2 = []
##        temp3 = []
##        temp4 = []
##        test_out = [[0,0],[360,360],[0,0],[360,360]]
##        for r in a:
##            if(r.group_idx[0]==0):
##                temp1.append(r.dims['d3']['par'])
##
##            if(r.group_idx[0]==1):
##                temp2.append(r.dims['d3']['par'])
##
##            if(r.group_idx[0]==2):
##                temp3.append(r.dims['d3']['par'])
##
##            if(r.group_idx[0]==3):
##                temp4.append(r.dims['d3']['par'])
##
##        print temp1
##        print temp2
##        print temp3
##        print temp4
##        output = [temp1,temp2,temp3,temp4]
##        assert output == test_out
##
############################################################################################
##        
##class Test_d2(object):
##    def test_d2_d1_par(self):
##        md_kernel, a = repex_initialize()
##        temp1 = []
##        temp2 = []
##        temp3 = []
##        temp4 = []
##        test_out = [[0,0],[0,0],[360,360],[360,360]]
##        for r in a:
##            if(r.group_idx[1]==0):
##                temp1.append(r.dims['d1']['par'])
##
##            if(r.group_idx[1]==1):
##                temp2.append(r.dims['d1']['par'])
##
##            if(r.group_idx[1]==2):
##                temp3.append(r.dims['d1']['par'])
##
##            if(r.group_idx[1]==3):
##                temp4.append(r.dims['d1']['par'])
##
##        print temp1
##        print temp2
##        print temp3
##        print temp4
##        output = [temp1,temp2,temp3,temp4]
##        assert output == test_out
##        
##
##    def test_d2_d2_par(self):
##        md_kernel, a = repex_initialize()
##        temp1 = []
##        temp2 = []
##        temp3 = []
##        temp4 = []
##        test_out = [[300,600],[300,600],[300,600],[300,600]]
##        for r in a:
##            if(r.group_idx[1]==0):
##                temp1.append(r.dims['d2']['par'])
##
##            if(r.group_idx[1]==1):
##                temp2.append(r.dims['d2']['par'])
##
##            if(r.group_idx[1]==2):
##                temp3.append(r.dims['d2']['par'])
##
##            if(r.group_idx[1]==3):
##                temp4.append(r.dims['d2']['par'])
##        
##        print temp1
##        print temp2
##        print temp3
##        print temp4
##        output = [temp1,temp2,temp3,temp4]
##        assert output == test_out
##        
##
##    def test_d2_d3_par(self):
##        md_kernel, a = repex_initialize()
##        temp1 = []
##        temp2 = []
##        temp3 = []
##        temp4 = []
##        test_out = [[0,0],[360,360],[0,0],[360,360]]
##        for r in a:
##            if(r.group_idx[1]==0):
##                temp1.append(r.dims['d3']['par'])
##
##            if(r.group_idx[1]==1):
##                temp2.append(r.dims['d3']['par'])
##
##            if(r.group_idx[1]==2):
##                temp3.append(r.dims['d3']['par'])
##
##            if(r.group_idx[1]==3):
##                temp4.append(r.dims['d3']['par'])
##
##        print temp1
##        print temp2
##        print temp3
##        print temp4
##        output = [temp1,temp2,temp3,temp4]
##        assert output == test_out
##
####################################################################################################
##class Test_d3(object):
##    def test_d3_d1_par(self):
##        md_kernel, a = repex_initialize()
##        temp1 = []
##        temp2 = []
##        temp3 = []
##        temp4 = []
##        test_out = [[0,0],[0,0],[360,360],[360,360]]
##        for r in a:
##            if(r.group_idx[2]==0):
##                temp1.append(r.dims['d1']['par'])
##
##            if(r.group_idx[2]==1):
##                temp2.append(r.dims['d1']['par'])
##
##            if(r.group_idx[2]==2):
##                temp3.append(r.dims['d1']['par'])
##
##            if(r.group_idx[2]==3):
##                temp4.append(r.dims['d1']['par'])
##
##        print temp1
##        print temp2
##        print temp3
##        print temp4
##        output = [temp1,temp2,temp3,temp4]
##        assert output == test_out
##        
##
##    def test_d3_d2_par(self):
##        md_kernel, a = repex_initialize()
##        temp1 = []
##        temp2 = []
##        temp3 = []
##        temp4 = []
##        test_out = [[300,300],[600,600],[300,300],[600,600]]
##        for r in a:
##            if(r.group_idx[2]==0):
##                temp1.append(r.dims['d2']['par'])
##
##            if(r.group_idx[2]==1):
##                temp2.append(r.dims['d2']['par'])
##
##            if(r.group_idx[2]==2):
##                temp3.append(r.dims['d2']['par'])
##
##            if(r.group_idx[2]==3):
##                temp4.append(r.dims['d2']['par'])
##        
##        print temp1
##        print temp2
##        print temp3
##        print temp4
##        output = [temp1,temp2,temp3,temp4]
##        assert output == test_out
##        
##
##    def test_d3_d3_par(self):
##        md_kernel, a = repex_initialize()
##        temp1 = []
##        temp2 = []
##        temp3 = []
##        temp4 = []
##        test_out = [[0,360],[0,360],[0,360],[0,360]]
##        for r in a:
##            if(r.group_idx[2]==0):
##                temp1.append(r.dims['d3']['par'])
##
##            if(r.group_idx[2]==1):
##                temp2.append(r.dims['d3']['par'])
##
##            if(r.group_idx[2]==2):
##                temp3.append(r.dims['d3']['par'])
##
##            if(r.group_idx[2]==3):
##                temp4.append(r.dims['d3']['par'])
##
##        print temp1
##        print temp2
##        print temp3
##        print temp4
##        output = [temp1,temp2,temp3,temp4]
##        assert output == test_out
##
##
####################################################################################################################        
##    def test_initialize_replica_d1_param(self):
##        md_kernel, a = repex_initialize()
##        test_out = [{'type': 'umbrella', 'par': 0.0, 'old_par': 0.0},
##                    {'type': 'umbrella', 'par': 0.0, 'old_par': 0.0},
##                    {'type': 'umbrella', 'par': 0.0, 'old_par': 0.0},
##                    {'type': 'umbrella', 'par': 0.0, 'old_par': 0.0},
##                    {'type': 'umbrella', 'par': 360.0, 'old_par': 360.0},
##                    {'type': 'umbrella', 'par': 360.0, 'old_par': 360.0},
##                    {'type': 'umbrella', 'par': 360.0, 'old_par': 360.0},
##                    {'type': 'umbrella', 'par': 360.0, 'old_par': 360.0}
##                    ]        
##        replica_output = []
##        for i in range(0,len(a)):
##            replica_output.append(a[i].dims['d1'])
##            print a[i].dims['d1']
##        #print replica_output
##        assert replica_output == test_out
##
##    def test_initialize_replica_d2_param(self):
##        md_kernel, a = repex_initialize()
##        test_out = [{'type': 'temperature', 'par': 300.0, 'old_par': 300.0},
##                    {'type': 'temperature', 'par': 300.0, 'old_par': 300.0},
##                    {'type': 'temperature', 'par': 600.0, 'old_par': 600.0},
##                    {'type': 'temperature', 'par': 600.0, 'old_par': 600.0},
##                    {'type': 'temperature', 'par': 300.0, 'old_par': 300.0},
##                    {'type': 'temperature', 'par': 300.0, 'old_par': 300.0},
##                    {'type': 'temperature', 'par': 600.0, 'old_par': 600.0},
##                    {'type': 'temperature', 'par': 600.0, 'old_par': 600.0}
##                    ]
##        replica_output = []
##        for i in range(0,len(a)):
##            replica_output.append(a[i].dims['d2'])
##            print a[i].dims['d3']
##        print replica_output
##        assert replica_output == test_out
##
##    def test_initialize_replica_d3_param(self):
##        md_kernel, a = repex_initialize()
##        test_out = [{'type': 'umbrella', 'par': 0.0, 'old_par': 0.0},
##                    {'type': 'umbrella', 'par': 360.0, 'old_par': 360.0},
##                    {'type': 'umbrella', 'par': 0.0, 'old_par': 0.0},
##                    {'type': 'umbrella', 'par': 360.0, 'old_par': 360.0},
##                    {'type': 'umbrella', 'par': 0.0, 'old_par': 0.0},
##                    {'type': 'umbrella', 'par': 360.0, 'old_par': 360.0},
##                    {'type': 'umbrella', 'par': 0.0, 'old_par': 0.0},
##                    {'type': 'umbrella', 'par': 360.0, 'old_par': 360.0}
##                    ]
##        replica_output = []
##        for i in range(0,len(a)):
##            replica_output.append(a[i].dims['d3'])
##            print a[i].cycle
##        #print replica_output
##        assert replica_output == test_out
##    
## 
##class Test_func(object):
##    def test_shared_files(self):
##        md_kernel,a = repex_initialize_shared_data()
##        test_files = ['ace_ala_nme.parm7',
##                      'ace_ala_nme.mdin',
##                      'matrix_calculator_temp_ex.py',
##                      'matrix_calculator_us_ex.py',
##                      'input_file_builder.py',
##                      'global_ex_calculator.py',
##                      'ace_ala_nme_double.RST',
##                      'salt_conc_pre_exec.py',
##                      'salt_conc_post_exec.py',
##                      'ace_ala_nme.inpcrd.0.0.0']
##        replica_output = md_kernel.shared_files
##        #print md_kernel.shared_urls
##        assert replica_output == test_files
##
####    def test_prepare_replica_for_md(self):
####        import radical.pilot
####        
####        md_kernel,a = repex_initialize_shared_data()
####        shared_input_files = md_kernel.shared_files
####        sd_shared_list=[]
####        for i in range(len(shared_input_files)):
####            sd_shared = {'source': 'staging:///%s' % shared_input_files[i],
####                         'target': shared_input_files[i],
####                         'action': radical.pilot.COPY
####            }
####            sd_shared_list.append(sd_shared)
####        a[0].state = 'W'
####        compute_replica = md_kernel.prepare_replica_for_md(3,'d1',a,a[0],sd_shared_list)
####        print compute_replica.post_exec
####        print n
####        assert compute_replica == 'hello'
####        
####        
####
##
##
##    
