.. _gettingstarted:

***************
Getting Started
***************

In this section we will briefly describe how RepEx can be invoked, how input and 
resource configuration files should be used.

Invoking RepEx
==============

To run RepEx users need to use a command line tool corresponding to MD package 
kernel they intend to use. For example, if user wants to use Amber as MD kernel, 
she would use ``repex-amber`` command line tool. In addition to specifying an 
appropriate command line tool, user need to specify a resource configuration file 
and REMD simulation input file. The resulting invocation of RepEx should be:

``repex-amber --input='tuu_remd_ace_ala_nme.json' --rconfig='stampede.json'``

where:

``--input=`` - specifies the REMD simulation input file

``--rconfig=`` - specifies resource configuration file

Both REMD simulation input file and resource configuration file must conform to
JSON format.

Resource configuration file
---------------------------

In resource configuration file **must** be provided the following parameters:

 - ``resource`` - this is the name of the target machine. Currently supported machines are:

     ``local.localhost`` - your local system

     ``xsede.stampede`` - Stampede supercomputer at TACC

     ``xsede.supermic`` - SuperMIC supercomputer at LSU

     ``xsede.comet`` - Comet supercomputer at SDSC

     ``xsede.gordon`` - Gordon supercomputer at SDSC

     ``epsrc.archer`` - Archer supercomputer at EPCC

     ``ncsa.bw_orte`` - Blue Waters supercomputer at NCSA


 - ``username`` - your username on the target machine

 - ``project`` - your allocation on specified machine

 - ``cores`` - number of cores you would like to allocate

 - ``runtime`` - for how long you would like to allocate cores on target machine (in minutes).

In addition are provided the following **optional** parameters:

 - ``queue`` - specifies which queue to use for job submission. Values are machine specific.

 - ``cleanup`` - specifies if files on remote machine must be deleted. Possible values are: ``True`` or ``False``

 - ``mongo_url`` - url to your own Mongo DB instance

Example resource configuration file for Stampede supercomputer might look like this:

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

