#RepEX: Replica Exchange simulations Package

This package is aimed to provide functionality to run Replica Exchange simulations using various RE schemes and MD kernels. Currectly RepEX supports NAMD as it's application kernel and allows to perform RE simulations on local and remote systems. Functionality to run three RE schemes is available.

###Theory of Replica Exchange simulations

In Parallel Tempering (Replica Exchange) simulations N replicas of the original system are used to model phenomenon of interest. Typically, each replica can be treated as an independent system and would be initialised at a different temperature. While systems with high temperatures are very good at  sampling large portions of phase space, low temperature systems often become trapped in local energy minima during the simulation. Replica Exchange method is very effective in addressing this issue and generally demonstrates a very good sampling. In RE simulations, system replicas of both higher and lower temperature sub-sets are present. During the simulation they exchange full configurations at different temperatures, allowing lower temperature systems to sample a representative portion of phase space.

###RE scheme 1

This is the conventional RE scheme where all replicas first run MD for a fixed period of simulation time (e.g. 2 ps) and then perform an exchange step. In this scheme a global barrier is present - all replicas must first finish MD run and only then exchnage step can occur. Main characteristics of this scheme are:
 - number of replicas equals to the number of allocated compute cores
 - simultaneous MD
 - simultaneous exchange
 - all replicas participate in exchange step
 - constant simulation cycle time
 - global barrier between MD and exchange step

###RE scheme 2

The main difference of this scheme from scheme 1 is in number of compute cores used for simulation, which is less than the number of replicas (typically 50% of the number of replicas). This small detail results in both MD run and exchange step being performed concurrently. At the same time global synchronization barrier is still present - no replica can start exchange before all replicas has finished MD and vice versa. We define exchange step as concurrent since this step isn't performed simultaneouslhy (in parallel) for all replicas. Similarly to scheme 1 in this scheme simulation cycle for each replica is defined as fixed number of simulation time-steps. This scheme can be summarized as:
 - number of allocated compute cores equals 50% of replicas
 - concurrent MD
 - concurrent exchange
 - all replicas participate in exchange step
 - constant simulation cycle time
 - global barrier between MD and exchange step

###RE scheme 3

This scheme is asynchronous - MD run on target resource is overlapped with exchange step. Similarly to scheme 2, the number of replicas exceeds allocated compute cores. Simulation cycle is defined as a fixed time interval during which replicas are performing MD run. After cycle time elapses, some of the replicas are still performing MD run but some are ready for exchange. At this point exchange step involving replicas which has finished MD run is performed. Main characteristics of this scheme are:
 - number of allocated compute cores equals 50% of replicas
 - no global synchronization barrier between MD and exchange step
 - simulation cycle is defined as fixed real time interval 
 - concurrent MD
 - only fraction of replicas participate in exchange step
 - during time period of simulation cycle no replicas participate in exchange step
 This scheme can be summarized as follows:
 - All replicas are initialized and assigned a "waiting" state
 - While elapsed time is less that the total simulation time, do:  
 		- All replicas in "waiting" state are submitted to target resource for execution
 		- State of all submitted replicas is changed to "running"
        - Wait for a fixed time interval (simulation cycle)
        - All replicas which has finished MD run are assigned state "waiting"
        - Exchange step is performed for all replicas in "waiting" state
       
##Installation instructions

```bash
$ virtualenv $HOME/myenv 
$ source $HOME/myenv/bin/activate 
$ git clone https://github.com/radical-cybertools/ReplicaExchange.git 
$ cd ReplicaExchange
$ python setup.py install
```

Then you can verify that Radical Pilot was installed correctly:
```bash
$ radicalpilot-version
```

This should print Radical Pilot version in terminal
 
##Usage

Current version of RepEx code supports three RE schemes described above. Before running any simulation user first must make appropriate changes to /src/radical/repex/config/input.json file. To run simulation examples using any of the RE schemes, no changes are required below the line starting with "input.NAMD", unless user wants to specify her/his own NAMD input files or change number of replicas used for simulation. Instructions on how to modify input.json file to run simulation examples locally, on Stampede [1] supercomputer and Trestles [2] supercomputer are provided in /src/radical/repex/config/config.info file.       

###Running simulation using RE scheme 1

To run RE simulation using this scheme in input.json "number_of_replicas" and "cores" values must be equal. This scheme can be run with exchange step being performed locally or remotelly. For RE simulation with remote exchange step in terminal execute: 
```bash
$ sh launcher_2.sh
```
For RE simulation with local exchange step in terminal execute:
```bash
$ sh launcher_2a.sh
``` 
This will run RE temperature exchange simulation involving X replicas on your target system. During the simulation input files for each of the replicas will be generated. After simulation is done in ReplicaExchange/src/radical/repex/ directory you will see a number of new "replica_x" directories. Each directory will contain simulation output files.   

###Running simulation using RE scheme 2

To run RE simulation using scheme 2 in input.json "number_of_replicas" must be greater than "cores". As mentioned above recommended "cores" value is 50% of the "number_of_replicas". As for scheme 1 two options with respect to exchange step are available. For RE simulation with remote exchange step in terminal execute: 
```bash
$ sh launcher_2.sh
```
For RE simulation with local exchange step in terminal execute:
```bash
$ sh launcher_2a.sh
``` 
After simulation is done, please verify existance of the output files in "replica_x" directories.

###Running simulation using RE scheme 3

In order to run RE simulation using this scheme key value pair <"cycle_time": "2"> must be added to "input.PILOT" dictionary in input.json file. Value of "cycle_time" specifies wall clock time in minutes for simulation cycle. For provided input recommended "cycle_time" value is 2. After this change is made to input.json file, simulation can be launched using the following command in terminal:
```bash
$ sh launcher_3.sh
```         
After simulation is done, please verify existance of the output files in "replica_x" directories.

