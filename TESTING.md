##Installation instructions

Currently it is recommended to use development versions of both SAGA-Python and Radical Pilot in conjunction with RepEx.

```bash
virtualenv $HOME/myenv 
source $HOME/myenv/bin/activate
git clone -b devel https://github.com/radical-cybertools/saga-python.git
cd saga-python
python setup.py install
cd ..
git clone -b devel https://github.com/radical-cybertools/radical.pilot.git
cd radical.pilot
python setup.py install
cd .. 
git clone https://github.com/radical-cybertools/RepEx.git 
cd RepEx
python setup.py install
```

Then you can verify that Radical Pilot was installed correctly:
```bash
radicalpilot-version
```

This should print Radical Pilot version in terminal
 
##Usage

Current version of RepEx code supports three RE schemes described above. Before running her/his simulation user must make appropriate changes to /src/radical/repex/config/<kernel_name>_input.json file. To run simulation examples using any of the RE schemes, no changes are required below the line starting with "input.MD", unless user wants to specify her/his own MD input files or change number of replicas used for simulation. Instructions on how to modify <kernel_name>_input.json file to run simulation examples locally, on Stampede [1] supercomputer and Trestles [2] supercomputer are provided in /src/radical/repex/config/config.info file.       
Before running any of the provided examples users must first change directory to:

```bash
cd /src/radical/repex/
```

###Running simulation using RE scheme 1

To run RE simulation using this scheme and NAMD kernel in namd_input.json "number_of_replicas" and "cores" values must be equal. For this scheme exchange step can be performed locally or remotelly. For RE simulation with remote exchange step in terminal execute: 
```bash
python launch_simulation_scheme_1_namd.py --input='config/namd_input.json'
```
For RE simulation with local exchange step in terminal execute:
```bash
python launch_simulation_scheme_1a_namd.py --input='config/namd_input.json'
``` 
This will run RE temperature exchange simulation involving X replicas on your target system. During the simulation input files for each of the replicas will be generated. After simulation is done in RepEx/src/radical/repex/ directory you will see a number of new "replica_x" directories. Each directory will contain simulation output files. 


To run RE simulation using scheme 1 and Amber kernel you will need to modify amber_input.json file so that "number_of_replicas" and "cores" values are equal. For RE simulation with remote exchange step in terminal execute: 
```bash
python launch_simulation_scheme_1_amber.py --input='config/amber_input.json'
```
For RE simulation with local exchange step in terminal execute:
```bash
python launch_simulation_scheme_1a_amber.py --input='config/amber_input.json'
``` 

###Running simulation using RE scheme 2

To run RE simulation using scheme 2 and NAMD kernel in namd_input.json "number_of_replicas" must be greater than "cores". As mentioned previously recommended "cores" value is 50% of the "number_of_replicas". Similarly to scheme 1 two options with respect to exchange step are available. For RE simulation with remote exchange step in terminal execute: 
```bash
python launch_simulation_scheme_2_namd.py --input='config/namd_input.json'
```
For RE simulation with local exchange step in terminal execute:
```bash
python launch_simulation_scheme_2a_namd.py --input='config/namd_input.json'
``` 
After simulation is done, please verify existance of the output files in "replica_x" directories.


To run RE simulation using scheme 2 and Amber kernel you will need to modify amber_input.json file so that "number_of_replicas" is less than "cores". For RE simulation with remote exchange step in terminal execute: 
```bash
python launch_simulation_scheme_2_amber.py --input='config/amber_input.json'
```
For RE simulation with local exchange step in terminal execute:
```bash
python launch_simulation_scheme_2a_amber.py --input='config/amber_input.json'
``` 

###Running simulation using RE scheme 3

For this scheme it is recommended to add a key-value pair <"cycle_time": "integer_value"> to "input.MD" dictionary in <kernel_name>_input.json file. Value of "cycle_time" specifies wall clock time in minutes, which represents simulation cycle. If this key-value pair is not added default value of 1 minute will be used. Generally while changing "number_of_replicas" users will also need to adjust the value of "cycle_time", in order to maximize the number of replicas participating in each exchange step. After all changes (including those specified in /src/radical/repex/config/config.info file) are performed RE simulation can be launched using commands specified below.    

To run RE simulation using scheme 3 and NAMD kernel the following command must be executed in terminal:
```bash
python launch_simulation_scheme_3_namd.py --input='config/namd_input.json'
```  
To run RE simulation using scheme 3 and Amber kernel run:
```bash
python launch_simulation_scheme_3_amber.py --input='config/amber_input.json'
``` 
After simulation is done, please verify existance of the output files in "replica_x" directories.


###Troubleshooting

If your simulation fails for some reason the first thing to do is to re-run it with verbose flag:


```bash
RADICAL_PILOT_VERBOSE=info python <launcher_name>.py --input='config/<input_file>.json'
```

This will give you substantially more information about what is happening "under the bonnet" of the application. 