.. _multidimexamples:

**********************************
Multi-dimensional REMD simulations
**********************************

In addition to one-dimensional REMD simulations, RepEx also supports multi-dimensional REMD
simulations. With Amber Kernel currently supported are two three-dimensional usecases: 
 - TSU-REMD with one Temperature, one Salt Concentraiton and one Umbrella restraint dimension

 - TUU-REMD with one Temperature dimension and two Umbrella restraint dimensions

TUU-REMD example (alanine dipeptide) with Amber kernel
====================================================== 

For the example we will use Alanine Dipeptide (Ace-Ala-Nme) system. To run this example locally you must have Amber installed on your system. If you don't have Amber installed please download it from: ``http://ambermd.org/antechamber/download.html`` and install it using instructions at: ``http://ambermd.org/``

This guide assumes that you have already run example in getting-started section and 
are currently in ``amber`` directory, if not please cd into this directory from repex root directory:

.. parsed-literal:: cd examples/amber

Amongst other things in this directory are present:

 - ``tuu_remd_inputs`` - input files for TUU-REMD simulations

 - ``tuu_remd_ace_ala_nme.json`` - REMD input file for TUU-REMD usecase using Alanine Dipeptide system   

 - ``local.json`` - resource configuration file to run on local system (your laptop)

Run locally
-----------

To run this example locally you need to make appropriate changes to ``local.json`` resouce configuration file. We assume that you have already done this in getting started section.
Next you need to verify if parameters specified in ``tuu_remd_ace_ala_nme.json`` REMD input file satisfy your requirements. By default ``tuu_remd_ace_ala_nme.json`` file looks like this:

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
            	"number_of_replicas": "2",
            	"us_start_param": "0",
            	"us_end_param": "360"
            	},
        	"temperature_2": {
            	"number_of_replicas": "2",
            	"min_temperature": "300",
            	"max_temperature": "600"
            	},
        	"umbrella_sampling_3": {
            	"number_of_replicas": "2",
            	"us_start_param": "0",
            	"us_end_param": "360"
            	}    
    	}
	}

In comparison to REMD simulaiton input files used previously, this file has the following additional parameters:

 - ``input.dim`` - under this key must be specified parameters and names of individual dimensions for all multi-dimensional REMD simulations.

 - ``umbrella_sampling_1`` - indicates that first dimension is Umbrella potential

 - ``temperature_2`` - indicates that second dimension is Temperature

 - ``umbrella_sampling_1`` - indicates that third dimension is Umbrella potential

 - ``number_of_replicas`` - indicates number of replicas in this dimension

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
