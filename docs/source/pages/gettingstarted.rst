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

.. parsed-literal:: repex-amber --rconfig='local.json --input='t_remd_ace_ala_nme.json''

where:

``--rconfig=`` command line option for resource configuration file

``--input=`` command line option for simulation input file

Simulations with NAMD MD engine must be launched with:

``repex-namd --rconfig='local.json' --input='t_remd_ala.json'``


Resource configuration file
---------------------------

In resource configuration file **must** be provided the following parameters:

 - ``resource`` - this is the name of the target HPC cluster. Currently supported 
 systems are:

     ``local.localhost`` - your local workstation

     ``xsede.stampede``  - Stampede supercomputer (TACC)

     ``xsede.supermic``  - SuperMIC supercomputer (LSU)

     ``epsrc.archer``    - Archer supercomputer (EPCC)

     ``ncsa.bw``         - Blue Waters supercomputer (NCSA)


 - ``username`` - your username on target HPC cluster

 - ``project``  - your allocation on target HPC cluster

 - ``cores``    - number of CPU cores you would like to allocate

 - ``runtime``  - for how long you would like to allocate CPU cores on target HPC system (in minutes)

In addition user can provide the following **optional** parameters:

 - ``queue`` - specifies which queue to use for job submission (machine specific)

 - ``cleanup`` - specifies if files on remote machine must be deleted. Possible values are: ``True`` or ``False``

 - ``mongo_url`` - url to Mongo DB instance

 - ``access_schema`` - access schema (more info at: http://radicalpilot.readthedocs.io/en/latest/)

Example resource configuration file for Stampede HPC cluster might look like this:

.. parsed-literal::

	{
    	    "target": {
        	    "resource" : "xsede.stampede",
        	    "username" : "octocat",
        	    "project"  : "TG-XYZ123456",
        	    "queue"    : "development",
        	    "runtime"  : "30",
        	    "cleanup"  : "False",
        	    "cores"    : "16"
    	    }
	}


REMD input file for Amber kernel
--------------------------------

For use with Amber kernel, in REMD simulation input file **must** be provided the following parameters:

 - ``re_pattern`` - this parameter specifies Replica Exchange Pattern to use, options are: ``S`` - synchronous and ``A`` - asynchronous

 - ``exchange`` - this parameter specifies type of REMD simulation, for 1D simulation options are: ``T-REMD``, ``S-REMD`` and ``US-REMD``

 - ``number_of_cycles`` - number of cycles for a given simulation

 - ``number_of_replicas`` - number of replicas to use

 - ``input_folder`` - path to folder which contains simulation input files

 - ``input_file_basename`` - base name of generated input/output files

 - ``amber_input`` - name of input file template

 - ``amber_parameters`` - name of parameters file

 - ``amber_coordinates`` - name of coordinates file

 - ``replica_mpi`` - specifies if ``sander`` or ``sander.MPI`` is used for MD-step. Options are: ``True`` or ``False``

 - ``replica_cores`` - number of cores to use for MD-step for each replica, if ``replica_mpi`` is ``False`` this parameters must be equal to ``1`` 

 - ``steps_per_cycle`` - number of simulation time-steps

 - ``download_mdinfo`` - specifies if Amber .mdinfo files must be downloaded. Options are: ``True`` or ``False``. If this parameter is ommited, value defaults to "True"

 - ``download_mdout`` - specifies if Amber .mdout files must be downloaded. Options are: ``True`` or ``False``. If this parameter is ommited, value defaults to "True"

Optional parameters are specific to each simulation type. Example REMD simulation input file for T-REMD simulation might look like this:

.. parsed-literal::

	{
    	    "remd.input": {
        	    "re_pattern": "S",
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

