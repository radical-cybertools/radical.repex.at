.. _gettingstarted:

***************
Getting Started
***************

In this section we will describe how to use RepEx. We will explain available 
parameters for the resource configuration file and simulation input file.

Invoking RepEx
==============

RepEx provides two command line tools for launching REMD simulations: ``repex-amber`` 
and ``repex-namd``. As the names suggest, the former is designed for simulations with 
Amber MD engine, but the latter for simulations with NAMD MD engine.

For each of the two available command line tools for REMD simulations as a 
command line arguments must be provided exactly two input files:

  **resource configuration file**

  **simulation input file**

Both input files must conform to JSON format. Simulations with Amber MD engine 
must be launched with:

.. parsed-literal:: repex-amber --rconfig='local.json --input='t_remd_ace_ala_nme.json'

where:

    ``--rconfig=`` command line option for resource configuration file

    ``--input=`` command line option for simulation input file

Simulations with NAMD MD engine must be launched with:

.. parsed-literal:: repex-namd --rconfig='local.json' --input='t_remd_ala.json'


Resource configuration file
---------------------------

In resource configuration file **must** be provided the following parameters:

    ``resource`` -- *label of the target HPC cluster*

    ``username`` -- *your username on target HPC cluster*

    ``project``  -- *your allocation on target HPC cluster*

    ``cores``    -- *number of CPU cores you would like to allocate*

    ``runtime``  -- *for how long you would like to allocate CPU cores on target HPC system (in minutes)*

Currently supported HPC clusters are:

    ``local.localhost`` -- *your local workstation*

    ``xsede.stampede``  -- *Stampede supercomputer (TACC)*

    ``xsede.supermic``  -- *SuperMIC supercomputer (LSU)*

    ``epsrc.archer``    -- *Archer supercomputer (EPCC)*

    ``ncsa.bw``         -- *Blue Waters supercomputer (NCSA)*


In addition user can provide the following **optional** parameters:

    ``queue`` -- *specifies which queue to use for job submission (machine specific)*

    ``cleanup`` -- *specifies if files on remote machine must be deleted. Possible values are:* ``True`` *or* ``False``

    ``mongo_url`` -- *url to Mongo DB instance*

    ``access_schema`` -- *access schema (more info at:* http://radicalpilot.readthedocs.io/en/latest/ *)*

    ``sandbox`` -- *simulation's working directory on the file system of the target HPC resource*


Example resource configuration file for Stampede HPC cluster might look like this:

.. parsed-literal::

	{
        "resource" : "xsede.stampede",
        "username" : "octocat",
        "project"  : "TG-XYZ123456",
        "queue"    : "development",
        "runtime"  : "30",
        "cleanup"  : "False",
        "cores"    : "16"
	}


Simulation input file for Amber MD engine
-----------------------------------------

In simulation input file, under ``remd.input`` name, **must** be provided the following parameters:

    ``number_of_cycles`` -- *the number of simulation cycles*

    ``steps_per_cycle`` -- *number of simulation time-steps*

    ``input_folder`` -- *path to folder containing simulation input files*

    ``input_file_basename`` -- *base name for output files*

    ``amber_input`` -- *name of input file template*

    ``amber_parameters`` -- *name of parameters file*

    ``amber_coordinates_folder`` -- *path to folder containing coordinates files*

    ``us_template`` -- *specifies Amber's restraint (.RST) file. This parameter is required 
    only for simulations performing umbrella exchange.*

Additionally user can specify the following optional parameters (under ``remd.input`` name):

    ``sync`` -- *this parameter allows to specify synchronization options for the simulation. Available options are:* ``S`` *synchronous simulation and* ``A`` *asynchronous simulation. Default is synchronous simulation:* ``S``

    ``same_coordinates`` -- *specifies if the same coordinates file must be used for 
    all replicas. Possible values are:* ``True`` *or* ``False.`` *If this option is set to False, coordinates file for each replica* **must** *end with a postfix corresponding to numerical group index of this replica in each dumension (dot separated). For example, 
    coordinates file for a two-dimensional simulation for replica with group indexes 2 and 4 
    in dimensions 1 and 2 should have a postfix* **.2.4**. *Default value is* ``True.`` 

    ``replica_mpi`` -- *specifies if Amber's parallelized executable (pmemd.MPI or sander.MPI) should be used for MD simulation. Possible values are:* ``True`` *or* ``False.`` *If set to False (default), Amber's serial executable (sander) is used.*

    ``replica_cores`` -- *number of CPU cores to use for MD simulation (for each replica), if* ``replica_mpi`` *is* ``False`` *this parameters must be equal to 1. Default value is: 1.*

    ``download_mdinfo`` -- *specifies if Amber's* ``.mdinfo`` *files must be downloaded from HPC cluster to local workstation. Possible values are:* ``True`` *or* ``False.`` *Default value is:* ``False.``

    ``download_mdout`` -- *specifies if Amber's* ``.mdout`` *files must be downloaded from HPC cluster to local workstation. Possible values are:* ``True`` *or* ``False.`` *Default value is:* ``False.``

    ``copy_mdinfo`` -- *specifies if Amber's* ``.mdinfo`` *files must be copied from working directories of replicas to "staging area" on remote HPC cluster. Possible values are:* ``True`` *or* ``False.`` *Default value is:* ``False.``  

    ``group_exec`` -- *specifies if replicas in a single group are executed as a 
    single task. This option is available only for multi-dimensional simulations involving temperature and/or umbrella exchange. Possible values are:* ``True`` *or* ``False.`` *Default value is:* ``False.``

    ``restart`` -- *specifies if previously aborted simulation should be restarted. After every simulation cycle simulation state is written to simulation_objects_d_c.pkl file. If simulation failed, we can restart the simulation from the last saved state. Possible values are:* ``True`` *or* ``False.`` *Default value is:* ``False.``

    ``restart_file`` -- *if restart is set to* ``True`` *name of the restart file must be specified. This file can be one of the simulation_objects_d_c.pkl files, generated after every simulation cycle.*

    ``exchange_off`` -- *allows to turn the exchange calculations off. Possible values are:* ``True`` *or* ``False.`` *Default value is:* ``False.`` *If set to* ``True`` *only tasks performing MD simulation are submitted for execution. No exchange calculations will be performed and none of the replicas will exchange their respective parameters.* 



per dimension:

``exchange_mpi`` -- *specifies if MPI executable should be used for exchange calculations. Possible values are: True or False.*


Example simulation input file for T-REMD simulation might look like this:

.. parsed-literal::

	{
    	    "remd.input": {
        	    "sync": "S",
        	    "exchange": "T-REMD",
        	    "number_of_cycles": "4",
        	    "number_of_replicas": "16",
        	    "input_folder": "t_remd_inputs",
        	    "input_file_basename": "ace_ala_nme_remd",
        	    "amber_input": "ace_ala_nme.mdin",
        	    "amber_parameters": "ace_ala_nme.parm7",
        	    "amber_coordinates": "ace_ala_nme.inpcrd",
        	    "replica_mpi": "False",
        	    "replica_cores": "1",
        	    "min_temperature": "300",
        	    "max_temperature": "600",
        	    "steps_per_cycle": "1000",
                "download_mdinfo": "True",
                "download_mdout" : "True",
    	    }
	}

