#Replica Exchange simulations Package

Current version of this package aims at providing functionality to perform synchronous RE (temperature exchange) simulations with NAMD. 

In Parallel Tempering (Replica Exchange) simulations N replicas of the original system are used to model phenomenon of interest. Typically, each replica can be treated as an independent system and would be initialised at a different temperature. While systems with high temperatures are very good at  sampling large portions of phase space, low temperature systems often become trapped in local energy minima during the simulation. Replica Exchange method is very effective in addressing this issue and generally demonstrates a very good sampling. In RE simulations, system replicas of both higher and lower temperature sub-sets are present. During the simulation they exchange full configurations at different temperatures, allowing lower temperature systems to sample a representative portion of phase space.


##Installation instructions

```bash
$ virtualenv $HOME/myenv 
$ source $HOME/myenv/bin/activate 
$ pip install radical.pilot
$ git clone https://github.com/radical-cybertools/ReplicaExchange.git 
$ cd ReplicaExchange/re_package 
$ cd config
```

open input.json and change namd path, you can find namd paths for mac and linux in paths-to-namd.dat,
alternatively you can specify your own path 

```bash
$ RADICAL_PILOT_VERBOSE=debug python radical_re_namd.py --input='config/input.json' --resource='config/xsede.json'
```

##Usage

To run RE simulation, specify simulation configuration file and resource configuration file: 

```bash
$ RADICAL_PILOT_VERBOSE=debug python radical_re_namd.py --input='config/input.json' --resource='config/xsede.json'
```

Examples of these files can be found in re_package/config 

###input.json 

**input.PILOT**

In this part of input file must be specified Pilot releted paramers. 

- resource: name of the system to use

- sandbox: working directory on the target system

"cores" and "runtime" parameters will be removed later on from this file, 
since these should be defined by the package itself.

mongo_url - url to db

input.NAMD

In this part of json input file must be specified NAMD releted paramers. 

namd_path - path to NAMD executable on target system

input_file_basename - base name of NAMD input file. At this point user must 
specify path to all NAMD configuration files in this file, e.g. paths to .params, 
.pdb and .psf files must be spesified in this file. 

number_of_replicas - number of replicas user wants to launch on a target system

min_temperature - minimum temperature for replicas

max_temperature - maximum temperature for replicas  

timestep - timestep size

steps_per_cycle - number of steps each replica performs in one cycle

p.s. all other parameters must be specified in NAMD input file directly!

xsede.json 
----------

. . .


