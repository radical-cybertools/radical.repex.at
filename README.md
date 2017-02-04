#RepEx: Replica Exchange simulations Package

This package is aimed to provide functionality to run Replica Exchange simulations using various RE algorithms and MD kernels. Currently RepEX supports NAMD and Amber as it's application kernels and allows to perform RE simulations on local and remote systems. Functionality to run four RE execution patterns is available. More information can be found [here](http://radical-cybertools.github.io/RepEx/).

###Theory of Replica Exchange simulations

In Parallel Tempering (Replica Exchange) simulations N replicas of the original system are used to model phenomenon of interest. Typically, each replica can be treated as an independent system and would be initialised at a different temperature. While systems with high temperatures are very good at  sampling large portions of phase space, low temperature systems often become trapped in local energy minima during the simulation. Replica Exchange method is very effective in addressing this issue and generally demonstrates a very good sampling. In RE simulations, system replicas of both higher and lower temperature sub-sets are present. During the simulation they exchange full configurations at different temperatures, allowing lower temperature systems to sample a representative portion of phase space.

###Execution Pattern A

![](https://github.com/radical-cybertools/RepEx/blob/gh-pages/images/pattern-a.jpg)

This is conventional RE execution pattern where all replicas first perform an MD-step for a fixed period of simulation time (e.g. 2 ps) and then perform an Exchange-step. In this pattern a global barrier is present - all replicas must first finish MD-step and only then Exchnage-step can be performed. Main characteristics of this pattern are:
* number of replicas equals to the number of allocated compute cores
* simultaneous MD
* simultaneous Exchange
* all replicas participate in Exchange-step
* constant simulation cycle time
* global barrier between MD and Exchange step

###Execution Pattern B

![](https://github.com/radical-cybertools/RepEx/blob/gh-pages/images/pattern-b.jpg)

The main difference of this Pattern from Pattern A is a number of compute cores used for simulation, which is less than the number of replicas (typically 50% of the number of replicas). This small detail results in both MD-step and Exchange-step being performed concurrently. At the same time global synchronization barrier is still present - no replica can start exchange before all replicas has finished MD and vice versa. We define exchange step as concurrent since this step isn't performed simultaneouslhy (in parallel) for all replicas. Similarly to Pattern A in this pattern simulation cycle for each replica is defined as fixed number of simulation time-steps. This pattern can be summarized as:
* number of allocated compute cores equals 50% of replicas
* concurrent MD 
* concurrent exchange
* all replicas participate in Exchange step
* constant simulation cycle time
* global barrier between MD and exchange step

###Execution Pattern C

![](https://github.com/radical-cybertools/RepEx/blob/gh-pages/images/pattern-c.jpg)

This pattern is asynchronous - MD step on target resource is overlapped with local Exchange step. Similarly to Pattern B, the number of replicas exceeds allocated compute cores. Simulation cycle is defined as a fixed time interval, during which replicas are performing MD step. After cycle time elapses, some of the replicas are still performing MD step but some are ready for exchange. At this point exchange step involving replicas which has finished MD step is performed. Main characteristics of this pattern are:
* number of allocated compute cores equals 50% of replicas
* no global synchronization barrier between MD and Exchange step
* simulation cycle is defined as fixed real time interval 
* concurrent MD
* only subset of replicas participate in Exchange step
* during time period of simulation cycle no replicas participate in Exchange step

This pattern can be summarized as follows:
 * All replicas are initialized and assigned a "waiting" state
 * While elapsed time is less that the total simulation time, do:  
    * All replicas in "waiting" state are submitted to target resource for execution
 	* State of all submitted replicas is changed to "running"
    * Wait for a fixed time interval (simulation cycle)
    * All replicas which has finished MD run are assigned state "waiting"
    * Exchange step is performed for all replicas in "waiting" state
       
###Execution Pattern D

![](https://github.com/radical-cybertools/RepEx/blob/gh-pages/images/pattern-d.jpg)

This pattern is similar to Pattern A. The main difference is in definition of the 
simulation cycle. Contrary to Pattern A (and Pattern B) here simulation cycle is defined as 
a real time interval. That is, all replicas are performing MD step and after predefined real time interval elapses each of MD steps is cancelled. For the next cycle is used last of the periodically generated restart files. The main characteristics of this pattern are:
* number of replicas equals to the number of allocated compute cores
* simultaneous MD
* simultaneous exchange
* all replicas participate in exchange step
* simulation cycle is defined as fixed real time interval 
* global barrier between MD and Exchange step

##Installation instructions

First you need to create a directory in your home directory for this tutorial:
```
mkdir hello-repex
cd hello-repex
``` 
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
virtualenv $HOME/repex-env 
source $HOME/repex-env/bin/activate
```
In case if virtualenv is not available on your machine, follow these instructions:
```bash
wget --no-check-certificate https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.10.tar.gz
tar xzf virtualenv-1.10.tar.gz
python virtualenv-1.10/virtualenv.py $HOME/repex-env
source $HOME/repex-env/bin/activate
```
Now you can install RepEx:
```bash
git clone https://github.com/radical-cybertools/RepEx.git
cd RepEx
git checkout feature/enmd
python setup.py install
```
If installation completed successfully you are ready to go.

##Usage



