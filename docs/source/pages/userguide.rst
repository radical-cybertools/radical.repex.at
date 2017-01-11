.. _userguide:

**********
User guide
**********

In this section we will describe how to run REMD simulations with RepEx on your local system.
To run examples of this section you must have Amber installed on your system.
If you don't have Amber installed please download it from: ``http://ambermd.org/antechamber/download.html`` and install it using instructions at: ``http://ambermd.org/`` 

T-REMD example (peptide ala10) with Amber kernel
================================================

We will take a look at Temperature-Exchange REMD example using peptide ala10 system
with Amber simulations kernel. 

This guide assumes that you have already installed RepEx, if not please go back to installation section. To obtain input files, please clone repex-examples repository:

.. parsed-literal:: git clone https://github.com/antonst/repex.examples.git

Next you need to cd into directory where input files recide:

.. parsed-literal:: cd repex.examples/examples/amber

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
            "sync": "S",
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

US-REMD example using Alanine Dipeptide system with Amber kernel
================================================================

In addition to T-REMD simulations, RepEx also supports Umbrella Sampling (biasing potentials) 
and Salt Concentration (ionic strength) one-dimensional REMD simulations with Amber kernel.
In this section we will take a look at Umbrella Sampling - US-REMD example. 

For the example we will use Alanine Dipeptide (Ace-Ala-Nme) system. To run this example locally you must have Amber installed on your system. If you don't have Amber installed please download it from: ``http://ambermd.org/antechamber/download.html`` and install it using instructions at: ``http://ambermd.org/``

This guide assumes that you currently are in ``repex.examples/examples/amber`` directory, if not 
please cd into that directory:

.. parsed-literal:: cd repex.examples/examples/amber

Amongst other things in this directory are present:

 - ``us_remd_inputs`` - input files for US-REMD simulations

 - ``us_remd_ace_ala_nme.json`` - REMD input file for  Umbrella Sampling REMD example using Alanine Dipeptide system   

 - ``local.json`` - resource configuration file to run on local system (your laptop)

Run locally
-----------

To run this example locally you need to make appropriate changes to ``local.json`` resouce configuration file. We assume that you have already done this in getting started section.
Next you need to verify if parameters specified in ``us_remd_ace_ala_nme.json`` REMD input file satisfy your requirements. By default ``us_remd_ace_ala_nme.json`` file looks like this:

.. parsed-literal::

    {
        "remd.input": {
            "sync": "S",
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

To run this example, all you need to do is to specify path to ``sander`` executable on your laptop. To do that please add ``amber_path`` parameter under ``remd.input``. For example:

.. parsed-literal:: "amber_path": "/home/octocat/amber/amber14/bin/sander"

To get notified about important events during the simulation please specify in terminal:

.. parsed-literal:: export RADICAL_REPEX_VERBOSE=info

Now you can run this simulation by:

``repex-amber --input='us_remd_ace_ala_nme.json' --rconfig='local.json'``

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

TUU-REMD example (alanine dipeptide) with Amber kernel
====================================================== 

In addition to one-dimensional REMD simulations, RepEx also supports multi-dimensional REMD
simulations. For the Amber Kernel, we currently support two three-dimensional scenarios:

 - TSU-REMD with one Temperature, one Salt Concentraiton and one Umbrella restraint dimension

 - TUU-REMD with one Temperature dimension and two Umbrella restraint dimensions

For this example we will use Alanine Dipeptide (Ace-Ala-Nme) system. To run this example locally you must have Amber installed on your system.

This guide assumes that you currently are in ``repex.examples/examples/amber`` directory, if not 
please cd into that directory:

.. parsed-literal:: cd repex.examples/examples/amber

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
        "remd.input": {
            "sync": "S",
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
        "dim.input": {
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

In comparison to REMD simulation input files used previously, this file has the following additional parameters:

 - ``dim.input`` - under this key must be specified parameters and names of individual dimensions for all multi-dimensional REMD simulations.

 - ``umbrella_sampling_1`` - indicates that first dimension is Umbrella potential

 - ``temperature_2`` - indicates that second dimension is Temperature

 - ``umbrella_sampling_1`` - indicates that third dimension is Umbrella potential

 - ``number_of_replicas`` - indicates number of replicas in this dimension

To run this example, all you need to do is to specify path to ``sander`` executable on your laptop. To do that please add ``amber_path`` parameter under ``remd.input``. For example:

.. parsed-literal:: "amber_path": "/home/octocat/amber/amber14/bin/sander"

To get notified about important events during the simulation please specify in terminal:

.. parsed-literal:: export RADICAL_REPEX_VERBOSE=info

Now you can run this simulation by:

``repex-amber --input='tuu_remd_ace_ala_nme.json' --rconfig='local.json'``

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
