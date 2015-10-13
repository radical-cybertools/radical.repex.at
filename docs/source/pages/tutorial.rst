.. _tutorial:

********
Tutorial
********

In this tutorial we will run several 1D-REMD and 3D-REMD examples on Stampede and Archer 
supercomputers. This guide assumes that you have already installed RepEx and cloned RepEx repository during the installation. If you haven't installed RepEx, please follow the steps
in Installation section of this user guide. If you can't find location of radical.repex directory, please clone repository again:

.. parsed-literal:: git clone https://github.com/radical-cybertools/radical.repex.git

and cd into Amber examples directory where input files recide:

.. parsed-literal:: cd radical.repex/examples/amber

To run examples of this tutorial you will need to modify two resource configuration files - ``stampede.json`` and ``archer.json``. Once you have these two files properly configured you 
can use them for all examples of this tutorial.  

Running on Stampede
===================

To run on Stampede you need to make appropriate changes to ``stampede.json`` resouce configuration file. Open this file in your favorite text editor (``vim`` in this case):

.. parsed-literal:: vim stampede.json

By default this file looks like this:

.. parsed-literal::

    {
        "target": {
            "resource": "xsede.stampede",
            "username" : "octocat",
        	"project" : "bigthings",
            "runtime" : "30",
            "cleanup" : "False",
            "cores" : "16"
        }
    }

You need to modify two parameters in this file:

 - ``username`` - this should be your username on Stampede

 - ``project``  - this should be your allocation on Stampede

Running on Archer
=================

To run on Archer you need to make appropriate changes to ``archer.json`` resouce configuration file. Open this file in your favorite text editor (``vim`` in this case):

.. parsed-literal:: vim archer.json

By default this file looks like this:

.. parsed-literal::

	{
    	"target": {
        	"resource": "epsrc.archer",
        	"username" : "octocat",
        	"project" : "bigthings",
        	"runtime" : "40",
        	"cleanup" : "False",
        	"cores" : "24"
    	}
	}

You need to modify two parameters in this file:

 - ``username`` - this should be your username on Archer

 - ``project``  - this should be your allocation on Archer

At this point you are done with resource configuration files and are ready to run 
simulations.

T-REMD example (peptide ala10) with Amber kernel
================================================

First, we will take a look at Temperature-Exchange REMD example using peptide ala10 system
with Amber simulations kernel. You need to verify if parameters specified in ``t_remd_ala10.json`` REMD input file satisfy your requirements. By default ``t_remd_ala10.json`` file looks like this:

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
            "exchange_mpi": "False",
            "min_temperature": "300",
            "max_temperature": "600",
            "steps_per_cycle": "4000",
            "exchange_mpi": "False",
            "download_mdinfo": "True",
            "download_mdout" : "True"
        }
    }

In comparison with general REMD input file format discussed above this input file 
contains some additional parameters:

 - ``min_temperature`` - minimal temperature value to be assigned to replicas

 - ``max_temperature`` - maximal temperature value to be assigned to replicas (we use geometrical progression for temperature assignment)

 - ``exchange_mpi`` - specifies if exchange step should use MPI interface. Options are: ``True`` or ``False``

Since we are using a supercomputer to run REMD simulation we increase the nuber 
of replicas to use. Please set ``"number_of_replicas"`` to ``"16"``.

To get notified about important events during the simulation please specify in terminal:

.. parsed-literal:: export RADICAL_REPEX_VERBOSE=info

Now you are ready to run this simulation. If you want to run on Stampede run in terminal:

``repex-amber --input='t_remd_ala10.json' --rconfig='stampede.json'``

If you want to run on Archer run in terminal:

``repex-amber --input='t_remd_ala10.json' --rconfig='archer.json'``

Verify output
-------------

If simulation has successfully finished, last three lines of terminal log should be similar to:

.. parsed-literal::

    2015:10:11 18:49:59 6600   MainThread   radical.repex.amber   : [INFO    ] Simulation successfully finished!
    2015:10:11 18:49:59 6600   MainThread   radical.repex.amber   : [INFO    ] Please check output files in replica_x directories.
    2015:10:11 18:49:59 6600   MainThread   radical.repex.amber   : [INFO    ] Closing session.

You should see 17 new directories in your current path:

 - sixteen ``replica_x`` directories

 - one ``shared_files`` directory

If you want to check which replicas exchanged configurations during each cycle you can cd into 
``shared_files`` directory and check each of four ``pairs_for_exchange_x.dat`` files. In these files are recorded indexes of replicas exchanging configurations during each cycle.

If you want to check .mdinfo or .mdout files for some replica, you can find those files in 
corresponding ``replica_x`` directory. File format is ``ala10_remd_i_c.mdinfo`` where:

 - **i** is index of replica

 - **c** is current cycle   

Simulation output can similarly be verified for all other examples of this tutorial.  

US-REMD example using Alanine Dipeptide system with Amber kernel
================================================================

For the example we will use Alanine Dipeptide (Ace-Ala-Nme) system. In ``examples/amber`` directory are present:

 - ``us_remd_inputs`` - input files for US-REMD simulations

 - ``us_remd_ace_ala_nme.json`` - REMD input file for  Umbrella Sampling REMD example using Alanine Dipeptide system   

To run this example you need to verify if parameters specified in ``us_remd_ace_ala_nme.json`` REMD input file satisfy your requirements. By default ``us_remd_ace_ala_nme.json`` file looks like this:

.. parsed-literal::

	{
    	"remd.input": {
    	    "re_pattern": "S",
        	"exchange": "US-REMD",
        	"number_of_cycles": "4",
        	"number_of_replicas": "8",
        	"input_folder": "us_remd_inputs",
        	"input_file_basename": "ace_ala_nme_remd",
        	"amber_input": "ace_ala_nme.mdin",
        	"amber_parameters": "ace_ala_nme.parm7",
        	"amber_coordinates_folder": "ace_ala_nme_coors",
        	"same_coordinates": "True",
        	"us_template": "ace_ala_nme_us.RST",
        	"replica_mpi": "False",
        	"replica_cores": "1",
        	"us_start_param": "120",
        	"us_end_param": "160",
        	"init_temperature": "300.0",
        	"steps_per_cycle": "2000",
        	"exchange_mpi": "False",
            "download_mdinfo": "True",
            "download_mdout" : "True"
    	}
	}

In comparison with general REMD input file format discussed in getting-started section 
this input file contains some additional parameters:

 - ``same_coordinates`` - specifies if each replica should use an individual coordinates file. Options are: ``True`` or ``False``. If ``True`` is selected, in ``amber_coordinates_folder`` must be provided coordinate files for each replica. Format of coordinates file is: ``filename.inpcrd.x.y``, where ``filename`` can be any valid python string, ``inpcrd`` is required file extension, ``x`` is index of replica in 1st dimension and ``y`` is index of replica in second dimension. For one-dimensional REMD, ``y = 0`` 
 must be provided 

 - ``us_template`` - name of Restraints template file

 - ``us_start_param`` - starting value of Umbrella interval 

 - ``us_end_param`` - ending value of Umbrella interval

 - ``init_temperature`` - initial temperature to use

 - ``exchange_mpi`` - specifies if exchange step should use MPI interface. Options are: ``True`` or ``False``

Since we are using a supercomputer to run REMD simulation we increase the nuber 
of replicas to use. Please set ``"number_of_replicas"`` to ``"16"``.

Now you are ready to run this simulation. If you want to run on Stampede run in terminal:

``repex-amber --input='us_remd_ace_ala_nme.json' --rconfig='stampede.json'``

If you want to run on Archer run in terminal:

``repex-amber --input='us_remd_ace_ala_nme.json' --rconfig='archer.json'``

Output verification can be done similarly as for T-REMD example. 

TUU-REMD example (alanine dipeptide) with Amber kernel
====================================================== 

For the example we also will use Alanine Dipeptide (Ace-Ala-Nme) system. In ``examples/amber`` directory are present:

 - ``tuu_remd_inputs`` - input files for TUU-REMD simulations

 - ``tuu_remd_ace_ala_nme.json`` - REMD input file for TUU-REMD usecase using Alanine Dipeptide system   

To run this example you need to verify if parameters specified in ``tuu_remd_ace_ala_nme.json`` REMD input file satisfy your requirements. By default ``tuu_remd_ace_ala_nme.json`` file looks like this:

.. parsed-literal::

	{
    	"input.MD": {
        	"re_pattern": "S",
        	"exchange": "TUU-REMD",
        	"number_of_cycles": "4",
        	"input_folder": "tuu_remd_inputs",
        	"input_file_basename": "ace_ala_nme_remd",
        	"amber_input": "ace_ala_nme.mdin",
        	"amber_parameters": "ace_ala_nme.parm7",
        	"amber_coordinates_folder": "ace_ala_nme_coors",
        	"us_template": "ace_ala_nme_us.RST",
        	"replica_mpi": "False",
        	"replica_cores": "1",
        	"steps_per_cycle": "6000"
        	},
    	"input.dim": {
        	"umbrella_sampling_1": {
            	"number_of_replicas": "4",
            	"us_start_param": "0",
            	"us_end_param": "360"
            	},
        	"temperature_2": {
            	"number_of_replicas": "4",
            	"min_temperature": "300",
            	"max_temperature": "600"
            	},
        	"umbrella_sampling_3": {
            	"number_of_replicas": "4",
            	"us_start_param": "0",
            	"us_end_param": "360"
            	}    
    	}
	}

In comparison to general REMD simulaiton input file, this file has the following additional parameters:

 - ``input.dim`` - under this key must be specified parameters and names of individual dimensions for all multi-dimensional REMD simulations.

 - ``umbrella_sampling_1`` - indicates that first dimension is Umbrella potential

 - ``temperature_2`` - indicates that second dimension is Temperature

 - ``umbrella_sampling_1`` - indicates that third dimension is Umbrella potential

 - ``number_of_replicas`` - indicates number of replicas in this dimension

Now you are ready to run this simulation. If you want to run on Stampede run in terminal:

``repex-amber --input='tuu_remd_ace_ala_nme.json' --rconfig='stampede.json'``

If you want to run on Archer run in terminal:

``repex-amber --input='tuu_remd_ace_ala_nme.json' --rconfig='archer.json'``

Output verification can be done similarly as for T-REMD example. 

