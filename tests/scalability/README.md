Scalability Requirements
=========

Simulation level - up to 10000 replicas

Replica level - up to 12 cores per replica 


Scalability Tests
=========

Machines
-------------

1. Stampede

2. Trestles

3. Archer (?)

Tests
-------------

Test-1 (NAMD)
1 core replicas and variable number of replicas e.g.: 24, 48, 96, 192, 384, 768, 1536, 3072, 6144 and fixed simulation length

Test-2 (NAMD)
fixed number of replicas e.g. 24 and variable number of cores per replica: 1, 2, 4, 8, 16 and fixed simulation length

Test-3 (NAMD)
1 core replicas and fixed number of replicas e. g. 24 and variable size of individual/simulation level input files for replicas: 1MB, 8MB, 16MB, 32MB, 64MB, 128MB, 256MB

Test-4 (NAMD)
One simulation across two machines (Trestles + Stampede), 1 core replicas and variable number of replicas e.g.: 512, 1024, 2048, 4096


Data presentation
-------------

Test-1
X axis - number of replicas; Y axis - time to completion for the simulation

Test-2
X axis - number of cores per replica; Y axis - time to completion for the simulation

Test-3
X axis - input file size; Y axis - time to complete one cycle 

Test-4
N/A


Tools
-------------

Matplotlib (other options will be considered)

     
