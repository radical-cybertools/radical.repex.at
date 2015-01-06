import sys
import time
import numpy
import os
import datetime
import matplotlib.pyplot as plt


PWD    = os.path.dirname(os.path.abspath(__file__))

#-------------------------------------------------------------------------------

def gen_graph():

    avg_d1_md_times = []
    avg_d1_exchange_times = []
    avg_d1_post_processing_times = []

    avg_d2_md_times = []
    avg_d2_exchange_times = []
    avg_d2_post_processing_times = []

    err_d1_md_times = []
    err_d1_exchange_times = []

    err_d2_md_times = []
    err_d2_exchange_times = []

    ############################################################################################
    # 16/36
    d1_md_times = [30.365068, 23.243326, 39.238980, 26.049971]
    avg_d1_md_times.append( numpy.average(d1_md_times) )
    err_d1_md_times.append( numpy.max(d1_md_times) - numpy.min(d1_md_times)  )

    d1_exchange_times = [17.633499, 18.591730, 20.971262, 19.790247]
    avg_d1_exchange_times.append( numpy.average(d1_exchange_times) )
    err_d1_exchange_times.append( numpy.max(d1_exchange_times) - numpy.min(d1_exchange_times) )

    d1_post_processing_times = [1.142013, 1.107513, 1.226829, 1.179110]
    avg_d1_post_processing_times.append( numpy.average(d1_post_processing_times) )

    d2_md_times = [23.173125, 24.174089, 24.760682, 25.985568]
    avg_d2_md_times.append( numpy.average(d2_md_times) )
    err_d2_md_times.append( numpy.max(d2_md_times) - numpy.min(d2_md_times)  )

    d2_exchange_times = [299.278418, 300.332897, 300.609991, 304.977011]
    avg_d2_exchange_times.append( numpy.average(d2_exchange_times) )
    err_d2_exchange_times.append( numpy.max(d2_exchange_times) - numpy.min(d2_exchange_times) )

    d2_post_processing_times = [1.123575,  1.184252, 1.202368, 1.224300]
    avg_d2_post_processing_times.append( numpy.average(d2_post_processing_times) )

    ############################################################################################

    ############################################################################################
    # 32/64
    d1_md_times = [47.942245, 51.034666, 54.865566, 59.245667]
    avg_d1_md_times.append( numpy.average(d1_md_times) )
    err_d1_md_times.append( numpy.max(d1_md_times) - numpy.min(d1_md_times)  )

    d1_exchange_times = [37.954966, 45.005007, 46.641876, 49.765296]
    avg_d1_exchange_times.append( numpy.average(d1_exchange_times) )
    err_d1_exchange_times.append( numpy.max(d1_exchange_times) - numpy.min(d1_exchange_times) )

    d1_post_processing_times = [2.051948, 2.068023, 2.118892, 2.164410]
    avg_d1_post_processing_times.append( numpy.average(d1_post_processing_times) )

    d2_md_times = [39.154995, 41.624917, 41.764834, 48.789878]
    avg_d2_md_times.append( numpy.average(d2_md_times) )
    err_d2_md_times.append( numpy.max(d2_md_times) - numpy.min(d2_md_times)  )

    d2_exchange_times = [537.999549, 503.826832, 507.783619, 509.462987]
    avg_d2_exchange_times.append( numpy.average(d2_exchange_times) )
    err_d2_exchange_times.append( numpy.max(d2_exchange_times) - numpy.min(d2_exchange_times) )

    d2_post_processing_times = [2.109387, 2.190040, 2.193578, 2.238376]
    avg_d2_post_processing_times.append( numpy.average(d2_post_processing_times) )

    ############################################################################################

    ############################################################################################
    # 48/100
    d1_md_times = [63.787029, 74.965102, 76.678391, 79.181725]
    avg_d1_md_times.append( numpy.average(d1_md_times) )
    err_d1_md_times.append( numpy.max(d1_md_times) - numpy.min(d1_md_times)  )

    d1_exchange_times = [76.364180, 85.399939, 99.538133, 124.942916]
    avg_d1_exchange_times.append( numpy.average(d1_exchange_times) )
    err_d1_exchange_times.append( numpy.max(d1_exchange_times) - numpy.min(d1_exchange_times) )

    d1_post_processing_times = [3.243015, 3.355360, 3.543187 , 3.592909]
    avg_d1_post_processing_times.append( numpy.average(d1_post_processing_times) )

    d2_md_times = [58.254513, 63.563623, 67.449060 , 70.572281]
    avg_d2_md_times.append( numpy.average(d2_md_times) )
    err_d2_md_times.append( numpy.max(d2_md_times) - numpy.min(d2_md_times)  )

    d2_exchange_times = [912.163353, 905.610178, 915.804334, 893.212869]
    avg_d2_exchange_times.append( numpy.average(d2_exchange_times) )
    err_d2_exchange_times.append( numpy.max(d2_exchange_times) - numpy.min(d2_exchange_times) )

    d2_post_processing_times = [3.447294, 3.672728, 3.819255 , 3.680650]
    avg_d2_post_processing_times.append( numpy.average(d2_post_processing_times) )

    ############################################################################################

    ############################################################################################
    # 64/144
    d1_md_times = [212.831624, 281.641534, 325.362382, 378.973468]
    avg_d1_md_times.append( numpy.average(d1_md_times) )
    err_d1_md_times.append( numpy.max(d1_md_times) - numpy.min(d1_md_times)  )

    d1_exchange_times = [894.101361, 1119.278625, 1341.732825, 1546.084171]
    avg_d1_exchange_times.append( numpy.average(d1_exchange_times) )
    err_d1_exchange_times.append( numpy.max(d1_exchange_times) - numpy.min(d1_exchange_times) )

    d1_post_processing_times = [1.293790, 1.970460, 2.173539, 3.285890]
    avg_d1_post_processing_times.append( numpy.average(d1_post_processing_times) )

    d2_md_times = [239.204443, 293.300422, 343.175599, 386.051157]
    avg_d2_md_times.append( numpy.average(d2_md_times) )
    err_d2_md_times.append( numpy.max(d2_md_times) - numpy.min(d2_md_times)  )

    d2_exchange_times = [2360.290811, 2580.461033, 2712.887872, 3006.533633]
    avg_d2_exchange_times.append( numpy.average(d2_exchange_times) )
    err_d2_exchange_times.append( numpy.max(d2_exchange_times) - numpy.min(d2_exchange_times) )

    d2_post_processing_times = [1.564811, 2.292860, 3.129889, 3.853214]
    avg_d2_post_processing_times.append( numpy.average(d2_post_processing_times) )

    ############################################################################################

    ############################################################################################
    # 96/196
    d1_md_times = [297.533121, 425.375181, 482.533535, 603.246597]
    avg_d1_md_times.append( numpy.average(d1_md_times) )
    err_d1_md_times.append( numpy.max(d1_md_times) - numpy.min(d1_md_times)  )

    d1_exchange_times = [1339.765219, 1772.832662, 2133.089385,  2439.336980]
    avg_d1_exchange_times.append( numpy.average(d1_exchange_times) )
    err_d1_exchange_times.append( numpy.max(d1_exchange_times) - numpy.min(d1_exchange_times) )

    d1_post_processing_times = [2.070978, 3.085039, 4.716662, 6.925007]
    avg_d1_post_processing_times.append( numpy.average(d1_post_processing_times) )

    d2_md_times = [350.121035, 436.021209, 502.753755, 1131.344448]
    avg_d2_md_times.append( numpy.average(d2_md_times) )
    err_d2_md_times.append( numpy.max(d2_md_times) - numpy.min(d2_md_times)  )

    d2_exchange_times = [3115.322205, 3327.796531, 3848.560669,  4348.560669]
    avg_d2_exchange_times.append( numpy.average(d2_exchange_times) )
    err_d2_exchange_times.append( numpy.max(d2_exchange_times) - numpy.min(d2_exchange_times) )

    d2_post_processing_times = [2.604054, 3.894754, 5.711873, 6.311873]
    avg_d2_post_processing_times.append( numpy.average(d2_post_processing_times) )

    ############################################################################################

    avg_d1_md_times.sort(reverse=True)
    avg_d1_exchange_times.sort(reverse=True)
    avg_d1_post_processing_times.sort(reverse=True)

    avg_d2_md_times.sort(reverse=True)
    avg_d2_exchange_times.sort(reverse=True)
    avg_d2_post_processing_times.sort(reverse=True)

    err_d1_md_times.sort(reverse=True)
    err_d1_exchange_times.sort(reverse=True)

    err_d2_md_times.sort(reverse=True)
    err_d2_exchange_times.sort(reverse=True)


    N = 5

    ind = numpy.arange(N)    # the x locations for the groups
    width = 0.25     # the width of the bars: can also be len(x) sequence 
    plt.rc("font", size=8)

    sum_d1_post_proc = []
    for i in range(len(avg_d1_md_times)):
        sum_d1_post_proc.append(avg_d1_md_times[i] +  avg_d1_exchange_times[i]) 


    p1 = plt.bar(ind, avg_d1_md_times, width, color='lightskyblue', yerr=err_d1_md_times, edgecolor = "white")
    p2 = plt.bar(ind, avg_d1_exchange_times, width, color='yellowgreen', bottom=avg_d1_md_times, yerr=err_d1_exchange_times, edgecolor = "white" )
    p3 = plt.bar(ind, avg_d1_post_processing_times, width, color='lightcoral', bottom=sum_d1_post_proc, edgecolor = "white" )

    sum_d2_md_times = []
    for i in range(len(avg_d2_md_times)):
        sum_d2_md_times.append(sum_d1_post_proc[i] +  avg_d1_post_processing_times[i]) 


    p4 = plt.bar(ind, avg_d2_md_times, width, color='chocolate', bottom=sum_d2_md_times, yerr=err_d2_md_times, edgecolor = "white" )

    sum_d2_ex_times = []
    for i in range(len(avg_d2_exchange_times)):
        sum_d2_ex_times.append(sum_d2_md_times[i] +  avg_d2_md_times[i]) 

    p5 = plt.bar(ind, avg_d2_exchange_times, width, color='burlywood', bottom=sum_d2_ex_times, yerr=err_d2_exchange_times, edgecolor = "white" )

    sum_d2_post_proc = []
    for i in range(len(avg_d2_post_processing_times)):
        sum_d2_post_proc.append(sum_d2_ex_times[i] +  avg_d2_exchange_times[i]) 

    p6 = plt.bar(ind, avg_d2_post_processing_times, width, color='darkolivegreen', bottom=sum_d2_post_proc, edgecolor = "white" )

    ############################

    plt.ylabel('Time in seconds')
    plt.title('2D example with AMBER; pattern B; Average cycle time distribution; variable Pilot size/Number of Replicas', size=10)
    plt.xlim(-0.25, 4.5)
    plt.xticks(ind+width/2., ('96/196', '64/144', '48/100', '32/64', '16/36' ) )
    
    plt.xlabel('Pilot size/Replicas')
    plt.yticks(numpy.arange(0,9000,500))
    plt.legend((p1[0], p2[0], p3[0], p4[0], p5[0], p6[0]), ('D1: avg MD times', 
                                                             'D1: avg Exchange times', 
                                                             'D1: avg Post-processing times',
                                                             'D2: avg MD times', 
                                                             'D2: avg Exchange times', 
                                                             'D2: avg Post-processing times') )

    ###########################################
    for rect in p1:
        height = rect.get_height()        
        plt.text(rect.get_x() - 0.1, 0.2*height, '%d'%int(height), ha='center', va='bottom')


    i = 0
    for rect in p2:
        height = rect.get_height()        
        plt.text(rect.get_x() + 0.13, 0.5*height + avg_d1_md_times[i], '%d'%int(height), ha='center', va='bottom')
        i += 1


    i = 0
    for rect in p3:
        height = rect.get_height()        
        plt.text(rect.get_x() + 0.3, 0.5*height + sum_d1_post_proc[i], '%d'%int(height), ha='center', va='bottom')
        i += 1 

    i = 0
    for rect in p4:
        height = rect.get_height()        
        plt.text(rect.get_x() - 0.1, 1.2*height + sum_d2_md_times[i], '%d'%int(height), ha='center', va='bottom')
        i += 1

    i = 0
    for rect in p5:
        height = rect.get_height()        
        plt.text(rect.get_x() + 0.13, 0.5*height + sum_d2_ex_times[i], '%d'%int(height), ha='center', va='bottom')
        i += 1

    i = 0
    for rect in p6:
        height = rect.get_height()        
        plt.text(rect.get_x()+ 0.3, 0.5*height + sum_d2_post_proc[i], '%d'%int(height), ha='center', va='bottom')
        i += 1


    plt.savefig('repex-graph-1.png')
   

#-------------------------------------------------------------------------------

if __name__ == "__main__":
    
    gen_graph()
