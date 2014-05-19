#Replica Exchange simulations Package

Current version of this package provides functionality to perform synchronous RE (temperature exchange) simulations with NAMD. 

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

##Usage

Before running RE simulation the following changes must be made:

- path no NAMD executable must be specified; open input.json and change MAND path, you can find namd paths for mac and linux in paths-to-namd.dat (three precompiled NAMD executables are shipped with this installation), alternatively you can specify your own path

- Mongo DB url must be specified; in /re_package/config/input.json change "mongodb://url-of-your-mongo-db-instance" to actual url    

To run RE simulation, specify simulation configuration file and resource configuration file: 

```bash
$ RADICAL_PILOT_VERBOSE=debug python radical_re_namd.py --input='config/input.json' --resource='config/xsede.json'
```

Examples of these files can be found in re_package/config directory

###input.json 

**input.PILOT**

In this part of input file must be specified Pilot releted paramers. 

- resource: name of the system to use, this should correspond to resource name defined in resource configuration file, e.g. xsede.json  

- sandbox: working directory on the target system

- cores: number of cores the pilot should allocate on the target resource 

- runtime: estimated total run time (wall-clock time) in minutes of the ComputePilot

- mongo_url: url to MongoDB database

- cleanup: boolean variable to specify if ComputeUnit and pilot directories should be deleted or not  

**input.NAMD**

In this part of json input file must be specified NAMD releted paramers. 

- namd_path: path to NAMD executable on target system

- input_file_basename: base name of NAMD input file (.namd); this file is used to create individual input files for replicas 

- namd_structure: path to namd structure file (.psf)

- namd_coordinates: path to namd coordinates file (.pdb)

- namd_parameters: path to namd parameters file (.params) 

- number_of_replicas: number of replicas to be launched on a target system

- min_temperature: minimum temperature for replicas

- max_temperature: maximum temperature for replicas  

- steps_per_cycle: number of steps each replica performs in one cycle

- number_of_cycles: number of cycles to perform during simulation

All other parameters must be specified in NAMD input file directly!

###xsede.json 

In this file must be specified resource details for the target machine. Please check Radical Pilot documenation for further details: http://radicalpilot.readthedocs.org/en/latest/machconf.html 



