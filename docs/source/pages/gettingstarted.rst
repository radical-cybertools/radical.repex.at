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

T-REMD example (peptide ala10) with Amber kernel
================================================

We will take a look at Temperature-Exchange REMD example using peptide ala10 system
with Amber simulations kernel. To run this example locally you must have Amber installed on your system.
If you don't have Amber installed please download it from: ``http://ambermd.org/antechamber/download.html`` and install it using instructions at: ``http://ambermd.org/``

This guide assumes that you have already installed RepEx. In order to run examples, first 
you need to cd into directory where input files recide:

.. parsed-literal:: cd $HOME/repex-env/share/radical.repex/examples/amber

Amongst other things in this directory are present:

 - ``t_remd_inputs`` - input files for T-REMD simulations

 - ``t_remd_ala10.json`` - REMD input file for Temperature-Exchnage example using peptide ala10 system   

 - ``local.json`` - resource configuration file to run on local system (your laptop)

Run locally
-----------

To run this example locally you need to make appropriate changes to ``local.json`` resouce configuration file. You need to open this file in your favorite text editor (``vim`` in this case):

.. parsed-literal:: vim local.json

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

 - ``cores`` - change this parameter to number of cores supported by your laptop

Next you need to verify if parameters specified in ``t_remd_ala10.json`` REMD input file satisfy 
your requirements. By default ``t_remd_ala10.json`` file looks like this:

.. parsed-literal::

    {
        "remd.input": {
            "re_pattern": "S",
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
            "min_temperature": "300",
            "max_temperature": "600",
            "steps_per_cycle": "4000",
            "download_mdinfo": "True",
            "download_mdout" : "True"
        }
    }

In comparison with general REMD input file format discussed above this input file 
contains some additional parameters:

 - ``min_temperature`` - minimal temperature value to be assigned to replicas

 - ``max_temperature`` - maximal temperature value to be assigned to replicas (we use geometrical progression for temperature assignment)

To run this example, all you need to do is to specify path to ``sander`` executable on your laptop. To do that please add ``amber_path`` parameter under ``remd.input``. For example:

.. parsed-literal:: "amber_path": "/home/octocat/amber/amber14/bin/sander"

To get notified about important events during the simulation please specify in terminal:

.. parsed-literal:: export RADICAL_REPEX_VERBOSE=info

Now you can run this simulation by:

``repex-amber --input='t_remd_ala10.json' --rconfig='local.json'``

Verify output
-------------

If simulation has successfully finished, last three lines of terminal log should be similar to:

.. parsed-literal::

    2015:10:11 18:49:59 6600   MainThread   radical.repex.amber   : [INFO    ] Simulation successfully finished!
    2015:10:11 18:49:59 6600   MainThread   radical.repex.amber   : [INFO    ] Please check output files in replica_x directories.
    2015:10:11 18:49:59 6600   MainThread   radical.repex.amber   : [INFO    ] Closing session.

You should see nine new directories in your current path:

 - eight ``replica_x`` directories

 - one ``shared_files`` directory

If you want to check which replicas exchanged configurations during each cycle you can cd into 
``shared_files`` directory and check each of four ``pairs_for_exchange_x.dat`` files. In these files are recorded indexes of replicas exchanging configurations during each cycle.

If you want to check .mdinfo or .mdout files for some replica, you can find those files in 
corresponding ``replica_x`` directory. File format is ``ala10_remd_i_c.mdinfo`` where:

 - **i** is index of replica

 - **c** is current cycle   
