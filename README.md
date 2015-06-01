#RepEx: Replica Exchange simulations Package

This package is aimed to provide functionality to run Replica Exchange simulations using various RE schemes and MD kernels. Currently RepEX supports NAMD and Amber as it's application kernels and allows to perform RE simulations on local and remote systems. Functionality to run four RE schemes is available. More information can be found at: [RepEx](http://radical-cybertools.github.io/RepEx/)


###Theory of Replica Exchange simulations

In Parallel Tempering (Replica Exchange) simulations N replicas of the original system are used to model phenomenon of interest. Typically, each replica can be treated as an independent system and would be initialised at a different temperature. While systems with high temperatures are very good at  sampling large portions of phase space, low temperature systems often become trapped in local energy minima during the simulation. Replica Exchange method is very effective in addressing this issue and generally demonstrates a very good sampling. In RE simulations, system replicas of both higher and lower temperature sub-sets are present. During the simulation they exchange full configurations at different temperatures, allowing lower temperature systems to sample a representative portion of phase space.

###RE pattern-A

![](https://github.com/radical-cybertools/RepEx/blob/gh-pages/images/pattern-a.jpg)

This is the conventional RE pattern where all replicas first run MD for a fixed period of simulation time (e.g. 2 ps) and then perform an exchange step. In this pattern a global barrier is present - all replicas must first finish MD step and only then exchange step can occur. Main characteristics of pattern-A are:
* number of replicas equals to the number of allocated compute cores
* simultaneous MD
* simultaneous exchange
* all replicas participate in exchange step
* constant simulation cycle time
* global barrier between MD and exchange step

###RE pattern-B

![](https://github.com/radical-cybertools/RepEx/blob/gh-pages/images/pattern-b.jpg)

The main difference between pattern-B and pattern-A is in number of compute cores used for simulation, which is less than the number of replicas (typically 50% of the number of replicas). This small detail results in concurrency in both MD and exchange step. At the same time global synchronization barrier is still present - no replica can start exchange before all replicas has finished MD and vice versa. We define exchange step as concurrent since this step isn't performed simultaneouslhy (in parallel) for all replicas. Similarly to pattern-A in this pattern simulation cycle for each replica is defined as fixed number of simulation time-steps. Pattern-B can be summarized as:
* number of allocated compute cores equals 50% of replicas
* concurrent MD
* concurrent exchange
* all replicas participate in exchange step
* constant simulation cycle time
* global barrier between MD and exchange step

###RE pattern-C

![](https://github.com/radical-cybertools/RepEx/blob/gh-pages/images/pattern-c.jpg)

This pattern is asynchronous - MD step on target resource is overlapped with exchange step. Similarly to pattern-B, the number of replicas exceeds allocated compute cores. Simulation cycle is defined as a fixed time interval during which replicas are performing MD run. After cycle time elapses, some of the replicas are still performing MD step but some are ready for exchange. At this point exchange step involving replicas which has finished MD run is performed. Main characteristics of pattern-C are:
* number of allocated compute cores equals 50% of replicas
* no global synchronization barrier between MD and exchange step
* simulation cycle is defined as fixed real time interval 
* concurrent MD
* only fraction of replicas participate in exchange step
* during time period of simulation cycle no replicas participate in exchange step

This pattern can be summarized as follows:
 * All replicas are initialized and assigned a "waiting" state
 * While elapsed time is less that the total simulation time, do:  
    * All replicas in "waiting" state are submitted to target resource for execution
 	* State of all submitted replicas is changed to "running"
    * Wait for a fixed time interval (simulation cycle)
    * All replicas which has finished MD run are assigned state "waiting"
    * Exchange step is performed for all replicas in "waiting" state
       
###RE pattern-D

This pattern is similar to pattern-A. The main difference is in definition of the 
simulation cycle. Contrary to pattern-A (and pattern-B) here simulation cycle is defined as 
a real time interval. That is, all replicas are performing MD and after predefined real time interval elapses each of MD runs is cancelled. For the next cycle is used last of the periodically generated restart files. The main characteristics of this pattern are:
* number of replicas equals to the number of allocated compute cores
* simultaneous MD
* simultaneous exchange
* all replicas participate in exchange step
* simulation cycle is defined as fixed real time interval 
* global barrier between MD and exchange step

##Installation instructions

First you need to create a directory in your home directory for this tutorial:
```
mkdir tutorial
cd tutorial
``` 
One of the prerequisites for RepEx installation is Python version >= 2.7. You can check your Python version with:
```bash
python -V
```
If default Python version on your system is below 2.7, you will need to install Python 2.7.x. More information can be found at:
```
https://www.python.org/download 
```
The first step in installing RepEx is to create and activate a fresh Python virtualenv:
```bash
virtualenv $HOME/myenv 
source $HOME/myenv/bin/activate
```
In case if virtualenv is not available on your system, follow these instructions:
```bash
wget --no-check-certificate https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.10.tar.gz
tar xzf virtualenv-1.10.tar.gz
python virtualenv-1.10/virtualenv.py $HOME/myenv
source $HOME/myenv/bin/activate
```
Now you can install RepEx:
```bash
git clone -b feature/2d-prof https://github.com/radical-cybertools/RepEx.git
cd RepEx
python setup.py install
```
If installation completed successfully you are ready to go.

##Usage

Current version of RepEx code supports four RE patterns. Usage examples for each pattern using each of the two supported MD kernels are provided in:
```
/examples/<kernel_name>/<pattern_name> 
```
Before running any of the provided examples user must make appropriate changes to:
```
/examples/<kernel_name>/<pattern_name>/<kernel_name>_input.json 
```
To run each of the provided examples, it is required to change directory to:
```
/examples/<kernel_name>/<pattern_name> 
```
If user intends to run simulations on a remote resource password-less access via ssh must be configured. More information can be found at:
```
http://www.linuxproblem.org/art_9.html
```

####Usage example for scheme 1 with Amber kernel

First we must change directory to:
```
cd examples/amber/amber_scheme_1/
```
Then, make appropriate changes to file:
```
amber_input.json
```
Suggested changes are:
* "resource" must be: "stampede.tacc.utexas.edu"
* "username" must be changed to username assigned to user on that resource
* "project" must be changed to allocation number on target resource
* if you intend to run simulation on your local system (e.g. "localhost") under "input.MD" you must provide "amber_path" which is a path pointing to Amber executable on your system

For scheme 1 "number_of_replicas" and "cores" values must be equal. For this scheme exchange step is performed remotely. To run this example in terminal execute: 
```bash
python launch_simulation_scheme_1_amber.py --input='amber_input.json'
```
This will run RE temperature exchange simulation involving 16 replicas on target system. During the simulation input files for each of the replicas will be generated. After simulation is done in current directory you will see a number of new "replica_x" directories. These directories contain input and output files generated for a given replica. 

