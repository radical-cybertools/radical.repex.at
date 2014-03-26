===========
Radical Pilot based Replica Exchange Package (v0.1)
===========

Current version of this package aims at providing functionality to 
perform synchronous RE (temperature exchange) simulations with NAMD. 

Installation instructions
=========

Prerequisites
-------------

1.Radical Pilot

Install from master branch in a virtual environment:
 
$ virtualenv $HOME/myenv
$ source $HOME/myenv/bin/activate
$ pip install --upgrade -e git://github.com/radical-cybertools/radical.pilot.git@master#egg=radical-pilot

2.NAMD

To run this package you need to have >= NAMD/2.9 installed on target system  


3.Numpy

. . .


Installing from source
----------------------

$ git clone https://github.com/radical-cybertools/ReplicaExchange.git
$ cd re_package
$ python setup.py install

Usage
=========

To run RE simulaiton simulation configuration file and resource configuration file must
be passed through command line:

$ python radical_re_namd.py --input=<my_input_file> --resource=<my_resource_configuration_file>

Examples of these files can be found in re_package/config 

input.json 
----------

input.PILOT

In this part of input file must be specified Pilot releted paramers. 

resource - name of the system to use

sandbox - working directory on the target system

"cores" and "runtime" parameters will be removed later on from this file, 
since these should be defined by the package itself.

mongo_url - url to db

input.NAMD

In this part of json input file must be specified NAMD releted paramers. 

namd_path - path to NAMD executable on target system

input_file_basename - base name of NAMD input file. At this point user must 
specify path to all NAMD configuration files in this file.  

number_of_replicas - number of replicas user wants to launch on a target system

min_temperature - minimum temperature for replicas

max_temperature - maximum temperature for replicas  

timestep - timestep size

steps_per_cycle - number of steps each replica performs in one cycle

p.s. all other parameters must be specified in NAMD input file directly!

xsede.json 
----------

. . .


