#RepEx: Replica Exchange simulations Package

This package is aimed to provide functionality to run Replica Exchange simulations using various RE schemes and MD kernels. Currently RepEX supports NAMD and Amber as it's application kernels and allows to perform RE simulations on local and remote systems. Functionality to run four RE schemes is available. More information can be found at:
```
http://radical-cybertools.github.io/RepEx/
```

###Theory of Replica Exchange simulations

In Parallel Tempering (Replica Exchange) simulations N replicas of the original system are used to model phenomenon of interest. Typically, each replica can be treated as an independent system and would be initialised at a different temperature. While systems with high temperatures are very good at  sampling large portions of phase space, low temperature systems often become trapped in local energy minima during the simulation. Replica Exchange method is very effective in addressing this issue and generally demonstrates a very good sampling. In RE simulations, system replicas of both higher and lower temperature sub-sets are present. During the simulation they exchange full configurations at different temperatures, allowing lower temperature systems to sample a representative portion of phase space.

###RE scheme 1

This is the conventional RE scheme where all replicas first run MD for a fixed period of simulation time (e.g. 2 ps) and then perform an exchange step. In this scheme a global barrier is present - all replicas must first finish MD run and only then exchnage step can occur. Main characteristics of this scheme are:
* number of replicas equals to the number of allocated compute cores
* simultaneous MD
* simultaneous exchange
* all replicas participate in exchange step
* constant simulation cycle time
* global barrier between MD and exchange step

###RE scheme 2

The main difference of this scheme from scheme 1 is in number of compute cores used for simulation, which is less than the number of replicas (typically 50% of the number of replicas). This small detail results in both MD run and exchange step being performed concurrently. At the same time global synchronization barrier is still present - no replica can start exchange before all replicas has finished MD and vice versa. We define exchange step as concurrent since this step isn't performed simultaneouslhy (in parallel) for all replicas. Similarly to scheme 1 in this scheme simulation cycle for each replica is defined as fixed number of simulation time-steps. This scheme can be summarized as:
* number of allocated compute cores equals 50% of replicas
* concurrent MD
* concurrent exchange
* all replicas participate in exchange step
* constant simulation cycle time
* global barrier between MD and exchange step

###RE scheme 3

This scheme is asynchronous - MD run on target resource is overlapped with exchange step. Similarly to scheme 2, the number of replicas exceeds allocated compute cores. Simulation cycle is defined as a fixed time interval during which replicas are performing MD run. After cycle time elapses, some of the replicas are still performing MD run but some are ready for exchange. At this point exchange step involving replicas which has finished MD run is performed. Main characteristics of this scheme are:
* number of allocated compute cores equals 50% of replicas
* no global synchronization barrier between MD and exchange step
* simulation cycle is defined as fixed real time interval 
* concurrent MD
* only fraction of replicas participate in exchange step
* during time period of simulation cycle no replicas participate in exchange step
This scheme can be summarized as follows:
 * All replicas are initialized and assigned a "waiting" state
 * While elapsed time is less that the total simulation time, do:  
    * All replicas in "waiting" state are submitted to target resource for execution
 	* State of all submitted replicas is changed to "running"
    * Wait for a fixed time interval (simulation cycle)
    * All replicas which has finished MD run are assigned state "waiting"
    * Exchange step is performed for all replicas in "waiting" state
       
###RE scheme 4

This scheme is very similar to scheme 1. The main difference is in definition of the 
simulation cycle. Contrary to scheme 1 (and scheme 2) here simulation cycle is defined as 
a real time interval. That is, all replicas are performing MD and after predefined real time interval elapses each of MD runs is cancelled. For the next cycle is used last of the periodically generated restart files. The main characteristics of this scheme are:
* number of replicas equals to the number of allocated compute cores
* simultaneous MD
* simultaneous exchange
* all replicas participate in exchange step
* simulation cycle is defined as fixed real time interval 
* global barrier between MD and exchange step

##Installation instructions

One of the prerequisites for RepEx installation is Python version >= 2.7. You can check your Python version with:
```bash
python -V
```
If default Python version on your machine is below 2.7, you will need to install Python 2.7.x. More information on this can be found at:
```
https://www.python.org/download 
```
The first step in installing RepEx is to create and activate a fresh Python virtual environment:
```bash
virtualenv $HOME/myenv 
source $HOME/myenv/bin/activate
```
In case if virtual environment is not available on your machine, follow these instructions:
```bash
wget --no-check-certificate https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.10.tar.gz
tar xzf virtualenv-1.10.tar.gz
python virtualenv-1.10/virtualenv.py $HOME/myenv
source $HOME/myenv/bin/activate
```
Next you need to install radical-utils:
```bash
git clone -b devel https://github.com/radical-cybertools/radical.utils.git
cd radical.utils
python setup.py install
cd ..
```
After that saga-python must be installed:
```bash
pip install saga-python
```
or
```bash
easy_install saga-python
```
Next radical-pilot must be installed:
```bash
git clone https://github.com/radical-cybertools/radical.pilot.git
cd radical.pilot
python setup.py install
cd ..
```
Now you can install RepEx:
```bash
git clone https://github.com/radical-cybertools/RepEx.git
cd RepEx
python setup.py install
```
 
##Usage

Current version of RepEx code supports four RE schemes. Usage examples for each scheme using each of the two supported MD kernels are provided in:
```
RepEx/examples/<kernel_name>/<scheme_nr> 
```
Before running any of the provided examples user must make appropriate changes to:
```
RepEx/examples/<kernel_name>/<scheme_nr>/config/<kernel_name>_input.json 
```
It is required to change directory to:
```
RepEx/examples/<kernel_name>/<scheme_nr> 
```
If user intends to run simulations on a remote resource password-less access via ssh must be configured. More information can be found at:
```
http://www.linuxproblem.org/art_9.html
```

####Usage example for scheme 1 with Amber kernel

First user must make appropriate changes to:
```
RepEx/examples/amber/amber_scheme_1/config/amber_input.json
```
Suggested changes are:
* "resource" must be: "stampede.tacc.utexas.edu", "trestles.sdsc.xsede.org", "gordon.sdsc.xsede.org" or "localhost"
* "username" must be changed to username assigned to user on that resource
* "project" must be changed to allocation number on target resource
* if you intend to run simulation on your local system (e.g. "localhost") under "input.MD" you must provide "amber_path" which is a path pointing to Amber executable on your system

For scheme 1 "number_of_replicas" and "cores" values must be equal. For this scheme exchange step is performed remotely. To run this example in terminal execute (from RepEx/examples/amber/amber_scheme_1/): 
```bash
python launch_simulation_scheme_1_amber.py --input='config/amber_input.json'
```
This will run RE temperature exchange simulation involving 16 replicas on target system. During the simulation input files for each of the replicas will be generated. After simulation is done in current directory you will see a number of new "replica_x" directories. These directories contain input and output files generated for a given replica.

####Usage example for scheme 2 with Amber kernel

Again, we start by modifying input file:
```
RepEx/examples/amber/amber_scheme_2/config/amber_input.json
```
Suggested changes are:
* "resource" must be: "stampede.tacc.utexas.edu", "trestles.sdsc.xsede.org", "gordon.sdsc.xsede.org" or "localhost"
* "username" must be changed to username assigned to user on that resource
* "project" must be changed to allocation number on target resource
* if you intend to run simulation on your local system (e.g. "localhost") under "input.MD" you must provide "amber_path" which is a path pointing to Amber executable on your system
* "number_of_replicas" must be greater than "cores". Recommended "cores" value is 50% of the "number_of_replicas"

In this example exchange step is performed remotelly. To run this example in terminal execute (from RepEx/examples/amber/amber_scheme_2/): 
```bash
python launch_simulation_scheme_2_amber.py --input='config/amber_input.json'
```
This will run RE temperature exchange simulation involving 32 replicas on target system. Similarly as for scheme 1, generated outputs can be found in replica_x directories.

####Usage example for scheme 2a with Amber kernel

This example demonstrates functionality to perform exchange step locally.

First we modify input file:
```
RepEx/examples/amber/amber_scheme_2a/config/amber_input.json
```
Suggested changes are:
* "resource" must be: "stampede.tacc.utexas.edu", "trestles.sdsc.xsede.org", "gordon.sdsc.xsede.org" or "localhost"
* "username" must be changed to username assigned to user on that resource
* "project" must be changed to allocation number on target resource
* if you intend to run simulation on your local system (e.g. "localhost") under "input.MD" you must provide "amber_path" which is a path pointing to Amber executable on your system
* "number_of_replicas" must be greater than "cores". Recommended "cores" value is 50% of the "number_of_replicas" 

To run this example in terminal execute (from RepEx/examples/amber/amber_scheme_2a/): 
```bash
python launch_simulation_scheme_2a_amber.py --input='config/amber_input.json'
```
This will run RE temperature exchange simulation involving 32 replicas on target system.

####Usage example for scheme 3 with Amber kernel

For scheme 3 input file is slightly different than for all previous schemes:
```
RepEx/examples/amber/amber_scheme_3/config/amber_input.json
```
As you can see "number_of_cycles" field is gone but is added field "cycle_time". It is highly recommended to adjust "cycle_time" value to your setup, otherwise you will see either few or all replicas being submitted for the next cycle. Other suggested changes are:
* "resource" must be: "stampede.tacc.utexas.edu", "trestles.sdsc.xsede.org", "gordon.sdsc.xsede.org" or "localhost"
* "username" must be changed to username assigned to user on that resource
* "project" must be changed to allocation number on target resource
* if you intend to run simulation on your local system (e.g. "localhost") under "input.MD" you must provide "amber_path" which is a path pointing to Amber executable on your system
* "number_of_replicas" must be greater than "cores". Recommended "cores" value is 50% of the "number_of_replicas" 

To run this example in terminal execute (from RepEx/examples/amber/amber_scheme_3/): 
```bash
python launch_simulation_scheme_3_amber.py --input='config/amber_input.json'
```
This will run RE temperature exchange simulation involving 32 replicas on target system.

####Usage example for scheme 4 with Amber kernel

This scheme also has "cycle_time" field instead of "number_of_cycles" field. For the provided example value of "cycle_time" is relatively small (5 seconds). This is motivated by the need to cancel MD runs before they have actually finished. For their own examples users will need to adjust this parameter together with the "steps_per_cycle" parameter, which defines how many simulation time steps MD run should perform in case if it doesn't get cancelled. Notice, in comparison to all previous examples here value of "steps_per_cycle" parameter is significantly larger (250000). Again, users must change:
* "resource" to: "stampede.tacc.utexas.edu", "trestles.sdsc.xsede.org", "gordon.sdsc.xsede.org" or "localhost"
* "username" to username assigned to user on that resource
* "project" to allocation number on target resource
* "number_of_replicas" must be equal to "cores"

To run this example in terminal execute (from RepEx/examples/amber/amber_scheme_4/): 
```bash
python launch_simulation_scheme_4_amber.py --input='config/amber_input.json'
```
This will run RE temperature exchange simulation involving 16 replicas on target system.