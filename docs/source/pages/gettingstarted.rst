.. _gettingstarted:

***************
Getting Started
***************

In this section we will briefly describe how RepEx can be invoked, how input and 
resource configuration files should be used. We will also introduce two concepts, 
central to RepEx - Replica Exchange Patterns and Execution Strategies.  

Invoking RepEx
==============

To run RepEx users need to use a command line tool corresponding to MD package 
kernel they intend to use. For example, if user wants to use Amber as MD kernel, 
she would use ``repex-amber`` command line tool. In addition to specifying an 
appropriate command line tool, user need to specify a resource configuration file 
and REMD simulation input file. The resulting invocation of RepEx should be:

``repex-amber --input='tsu_remd_ace_ala_nme.json' --rconfig='stampede.json'``

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

     ``stampede.tacc.utexas.edu`` - Stampede supercomputer at TACC

     ``xsede.supermic`` - SuperMIC supercomputer at LSU

     ``xsede.comet`` - Comet supercomputer at SDSC

     ``gordon.sdsc.xsede.org`` - Gordon supercomputer at SDSC

     ``archer.ac.uk`` - Archer supercomputer at EPCC

     ``ncsa.bw_orte`` - Blue Waters supercomputer at NCSA


 - ``username`` - your username on the target machine

 - ``project`` - your allocation on specified machine

 - ``cores`` - number of cores you would like to allocate

 - ``runtime`` - for how long you would like to allocate cores on target machine (in minutes).

In addition are provided the following **optional** parameters:

 - ``queue`` - specifies which queue to use for job submission. Values are machine specific.

 - ``cleanup`` - specifies if files on remote machine must be deleted. Possible values are: ``True`` or ``False``

Example resource configuration file for Stampede supercomputer might look like this:

.. parsed-literal::

	{
    	    "target": {
        	    "resource" : "stampede.tacc.utexas.edu",
        	    "username" : "octocat",
        	    "project"  : "TG-XYZ123456",
        	    "queue"    : "development",
        	    "runtime"  : "30",
        	    "cleanup"  : "False",
        	    "cores"    : "16"
    	    }
	}


REMD input file
---------------

For use with Amber kernel, in REMD simulation input file **must** be provided the following parameters:

 - ``re_pattern`` - this parameter specifies Replica Exchange Pattern to use, options are: ``A`` and ``B``

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

Optional parameters are specific to each simulation type. Example REMD simulation input file for T-REMD simulation might look like this:

.. parsed-literal::

	{
    	    "remd.input": {
        	    "re_pattern": "A",
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
        	    "steps_per_cycle": "1000"
    	    }
	}

T-REMD example (peptide ala10) with Amber kernel
================================================

First we will take a look at Temperature-Exchnage REMD example using peptide ala10 system
with Amber simulations kernel. 

We need to cd into examples directory where input files recide: 

**Step 1** : ``cd examples/amber_inputs/t_remd_inputs``

Amongst other things in this directory are present:

 - ``t_remd_inputs`` - input files for T-REMD simulations

 - ``t_remd_ala10.json`` - REMD input file for Temperature-Exchnage example using peptide ala10 system   

 - ``local.json`` - resource configuration file to ron on local system (your laptop)

 - ``stampede.json`` - resource configuration file for Stampede supercomputer

Run locally
-----------

To run our example locally we need to make appropriate changes to ``local.json`` resouce configuration file. To do so we open this file in our favorite text editor (vim in this case):

**Step 2** : ``vim local.json``

By default this file looks like this:

.. parsed-literal::

    {
        "target": {
            "resource": "local.localhost",
            "username" : "octocat",
            "runtime" : "30",
            "cleanup" : "False",
            "cores" : "4"
        }
    }

You need to modify only two parameters in this file:

 - ``username`` - this should be your username on your laptop

 - ``cores`` - if you have less than 4 cores on your laptop please change this parameter to 1, 
               if you have more cores, feel free to leave this parameter unchanged 

Next we need to verify if parameters specified in ``t_remd_ala10.json`` REMD input file satisfy 
our requirements. By default ``t_remd_ala10.json`` file looks like this:

.. parsed-literal::

    {
        "remd.input": {
            "re_pattern": "A",
            "exchange": "T-REMD",
            "number_of_cycles": "4",
            "number_of_replicas": "8",
            "input_folder": "t_remd_inputs",
            "input_file_basename": "ala10_remd",
            "amber_input": "ala10.mdin",
            "amber_parameters": "ala10.prmtop",
            "amber_coordinates": "ala10_minimized.inpcrd",
            "replica_mpi": "False",
            "replica_cores": "1",
            "exchange_mpi": "False",
            "min_temperature": "300",
            "max_temperature": "600",
            "steps_per_cycle": "4000"
        }
    }

First you need to specify the path to ``sander`` executable on your laptop

Run remotely
------------

todo

Verify output
-------------

todo

