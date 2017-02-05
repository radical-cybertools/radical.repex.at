.. _examples:

********
Examples
********

In this section we will describe how to run RepEx examples with Amber and NAMD 
MD engines.

**It is assumed that you have already installed RepEx, if not please go back to 
installation section**.

Amber examples
===============

We will demonstrate how to run two one-dimensional REMD simulations and two 
three-dimensional REMD simulations with Amber engine. One-dimensional examples are:

    Temperature exchange (T-REMD) with peptide ala10

    Umbrella exchange (U-REMD) with alanine dipeptide

Three-dimensional examples are:

    Umbrella, Temperature, Umbrella exchange (TUU-REMD) with alanine dipeptide

    Temperature, Salt concentration and Umbrella exchange (TSU-REMD) with alanine dipeptide


Temperature exchange (T-REMD) with peptide ala10
-------------------------------------------------

In RepEx examples directory for Amber engine (``radical.repex/examples/amber``) are present the following files:

    ``t_remd_ala10.json`` -- *simulation input file for temperature exchange using peptide* ala10   

    ``t_remd_inputs`` -- *input files directory for temperature exchange simulations*

First we verify if parameters specified in ``t_remd_ala10.json`` simulation input 
file satisfy our requirements. By default ``t_remd_ala10.json`` file looks like this:

.. parsed-literal::

    {
        "remd.input": {
            "sync": "S",
            "number_of_cycles": "3",
            "input_folder": "t_remd_inputs",
            "input_file_basename": "ala10_remd",
            "amber_input": "ala10.mdin",
            "amber_parameters": "ala10.prmtop",
            "amber_coordinates_folder": "ala10_coors",
            "steps_per_cycle": "1000",
            "download_mdinfo": "True",
            "download_mdout" : "True"
    },
        "dim.input": {
            "d1": {
                "type" : "temperature",
                "number_of_replicas": "8",
                "min_temperature": "300.0",
                "max_temperature": "308.0"
            }
        }
    }

If we intend to run this example locally, the only **required** change is to add 
``"amber_path"`` parameter under ``"remd.input"`` key. If we use this simulation 
input file without any other changes, our REMD simulation will use 8 replicas 
and will run 3 simulation cycles, while performing 1000 time-steps between exchanges. 

To run this example locally, in terminal we execute:

``repex-amber --input='t_remd_ala10.json' --rconfig='local.json'``

To run this example on HPC cluster, we must specify appropriate resource configuration file. 
For example, if we want to run on Stampede, in terminal we will execute:

``repex-amber --input='t_remd_ala10.json' --rconfig='stampede.json'``

**Note:** before using any of the resource configuration files for HPC clusters, please 
make appropriate changes to those files (as described in previous section).

If simulation has successfully finished, one of the last lines of terminal log should be similar to:

.. parsed-literal::

    2015:10:11 18:49:59 6600   MainThread   radical.repex.amber   : [INFO    ] Simulation successfully finished!

In addition, in your working directory should be created ``simulation_output`` 
directory. In this directory you will find all ``pairs_for_exchange_d_c.dat`` 
files and all ``simulation_objects_d_c.pkl`` files, where:

    **d** -- *is dimension*

    **c** -- *is current cycle*  

If you want to check which replicas exchanged temperatures during the simulation, 
you can examine ``pairs_for_exchange_d_c.dat`` files. In these files are recorded 
indexes of replicas, which exchanged their temperatures.

Finally if you had set ``"download_mdinfo"`` and ``"download_mdout"`` parameters 
to ``True``, in ``simulation_output`` directory you will find all ``.mdinfo`` and 
``.mdout`` files generated during the simulation.   


Umbrella exchange (U-REMD) with alanine dipeptide
--------------------------------------------------

For this example we will use alanine dipeptide (Ace-Ala-Nme).

To run this example we first must make sure we are in RepEx's examples directory for Amber (assuming RepEx repository was cloned in ``$HOME`` ):

.. parsed-literal:: cd $HOME/radical.repex/examples/amber

In this directory we will find:

    ``us_remd_inputs`` -- *input files for U-REMD simulations*

    ``us_remd_ace_ala_nme.json`` -- *simulation input file for umbrella exchange example with alanine dipeptide*

For this example we will use ``us_remd_ace_ala_nme.json`` simulation input file. By default this file looks like this:

.. parsed-literal::

    {
        "remd.input": {
            "sync": "S",
            "number_of_cycles": "3",
            "input_folder": "us_remd_inputs",
            "input_file_basename": "ace_ala_nme_remd",
            "amber_input": "ace_ala_nme.mdin",
            "amber_parameters": "ace_ala_nme.parm7",
            "amber_coordinates_folder": "ace_ala_nme_coors",
            "us_template": "ace_ala_nme_us.RST",
            "init_temperature": "300.0",
            "steps_per_cycle": "1000",
            "download_mdinfo": "True",
            "download_mdout" : "True"
        },
        "dim.input": {
            "d1": {
                "type" : "umbrella",
                "number_of_replicas": "8",
                "min_umbrella": "0.0",
                "max_umbrella": "360.0"
            }
        }
    }

In comparison with simulation input file for temperature exchange example we have some new parameters. Under ``"remd.input"`` key we have:

    ``us_template`` -- *specifies Amber's restraint (.RST) file.*

    ``init_temperature`` -- *specifies  temperature value initially assigned to all replicas.*

Additionally, under ``"dim.input"`` we have:

    ``"min_umbrella"`` -- *minimum umbrella restraint value*

    ``"max_umbrella"`` -- *maximum umbrella restraint value*

Before running this example locally, we must make one **required** change: add 
``"amber_path"`` parameter under ``"remd.input"`` key. If we use this simulation 
input file without any other changes, this REMD simulation will use 8 replicas 
and will run 3 simulation cycles, while performing 1000 time-steps between exchanges.

To run this example locally, in terminal we execute:

``repex-amber --input='us_remd_ace_ala_nme.json' --rconfig='local.json'``

To run this example on HPC cluster, we must specify appropriate resource configuration file. 
For example, if we want to run on SuperMIC, in terminal we will execute:

``repex-amber --input='us_remd_ace_ala_nme.json' --rconfig='supermic.json'``

**Note:** before using any of the resource configuration files for HPC clusters, please 
make appropriate changes to those files (as described in previous section).

Output verification is identical to the one described for the temperature exchange example. If simulation has successfully finished, one of the last lines of terminal log should be similar to:

.. parsed-literal::

    2015:10:11 18:49:59 6600   MainThread   radical.repex.amber   : [INFO    ] Simulation successfully finished!


Umbrella, Temperature, Umbrella exchange (3D TUU-REMD) with alanine dipeptide
------------------------------------------------------------------------------

For this example we also will use alanine dipeptide. to run this example, first 
we must check if we are in correct examples directory: 

.. parsed-literal:: cd $HOME/radical.repex/examples/amber

In this directory are present:

    ``tuu_remd_inputs`` -- *input files for TUU-REMD simulations*

    ``tuu_remd_ace_ala_nme.json`` -- *simulation input file for TUU-REMD example with alanine dipeptide*

We will use ``tuu_remd_ace_ala_nme.json`` simulation input file to run this example. By default this file looks like this:

.. parsed-literal::

    {
        "remd.input": {
            "sync": "S",
            "number_of_cycles": "3",
            "input_folder": "tuu_remd_inputs",
            "input_file_basename": "ace_ala_nme_remd",
            "amber_input": "ace_ala_nme.mdin",
            "amber_parameters": "ace_ala_nme.parm7",
            "amber_coordinates_folder": "ace_ala_nme_coors",
            "us_template": "ace_ala_nme_us.RST",
            "steps_per_cycle": "1000",
            "download_mdinfo": "True",
            "download_mdout" : "true"
            },
        "dim.input": {
            "d1": {
                "type" : "umbrella",
                "number_of_replicas": "2",
                "min_umbrella": "0.0",
                "max_umbrella": "360.0"
                },
            "d2": {
                "type" : "temperature",
                "number_of_replicas": "2",
                "min_temperature": "300.0",
                "max_temperature": "308.0"
                },
            "d3": {
                "type" : "umbrella",
                "number_of_replicas": "2",
                "min_umbrella": "0.0",
                "max_umbrella": "360.0"
                }
        }
    }

Before running this example locally, we must add ``"amber_path"`` parameter under ``"remd.input"`` key. If we use this simulation input file without any other changes, 
this REMD simulation will use 8 replicas and will run 3 simulation cycles, while performing 1000 time-steps between exchanges.

To run this example locally, in terminal we execute:

``repex-amber --input='tuu_remd_ace_ala_nme.json' --rconfig='local.json'``

To run this example on HPC cluster, we must specify appropriate resource configuration file. 
For example, if we want to run on Blue Waters, in terminal we will execute:

``repex-amber --input='tuu_remd_ace_ala_nme.json' --rconfig='bw.json'``

**Note:** before using any of the resource configuration files for HPC clusters, please 
make appropriate changes to those files (as described in previous section).

Output verification is identical to the one described for the temperature exchange example. If simulation has successfully finished, one of the last lines of terminal log should be similar to:

.. parsed-literal::

    2015:10:11 18:49:59 6600   MainThread   radical.repex.amber   : [INFO    ] Simulation successfully finished!


Temperature, Salt concentration, Umbrella exchange (3D TSU-REMD) with alanine dipeptide
---------------------------------------------------------------------------------------

For this example we also will use alanine dipeptide. to run this example, first 
we must check if we are in correct examples directory: 

.. parsed-literal:: cd $HOME/radical.repex/examples/amber

In this directory are present:

    ``tsu_remd_inputs`` -- *input files for TSU-REMD simulations*

    ``tsu_remd_ace_ala_nme.json`` -- *simulation input file for TSU-REMD example with alanine dipeptide*

We will use ``tsu_remd_ace_ala_nme.json`` simulation input file to run this example. By default this file looks like this:

.. parsed-literal::

    {
        "remd.input": {
            "sync": "S",
            "number_of_cycles": "3",
            "input_folder": "tsu_remd_inputs",
            "input_file_basename": "ace_ala_nme_remd",
            "amber_input": "ace_ala_nme.mdin",
            "amber_parameters": "ace_ala_nme_old.parm7",
            "amber_coordinates_folder": "ace_ala_nme_coors",
            "us_template": "ace_ala_nme_us.RST",
            "steps_per_cycle": "1000",
            "download_mdinfo": "True",
            "download_mdout" : "True"
            },
        "dim.input": {
            "d1": {
                "type" : "temperature",
                "number_of_replicas": "2",
                "min_temperature": "300",
                "max_temperature": "302"
                },
            "d2": {
                "type" : "salt",
                "number_of_replicas": "2",
                "min_salt": "0.0",
                "max_salt": "1.0"
                },
            "d3": {
                "type" : "umbrella",
                "number_of_replicas": "2",
                "min_umbrella": "0",
                "max_umbrella": "360"
            }    
        }
    }

Under ``"d2"`` key we have two new parameters:

    ``min_salt`` -- *minimum salt concentration value*

    ``max_salt`` -- *maximum salt concentration value*

Before running this example locally we must add ``"amber_path"`` parameter **and** ``"amber_path_mpi"`` parameter under ``"remd.input"`` key. 

**Note:** To run this example locally you must have both ``sander`` and ``sander.MPI`` 
available on your workstation.

If we use this simulation input file without any other changes, we will run with 8 replicas for 3 simulation cycles, while performing 1000 time-steps between exchanges.

To run this example locally, in terminal we execute:

``repex-amber --input='tsu_remd_ace_ala_nme.json' --rconfig='local.json'``

To run this example on HPC cluster, we must specify appropriate resource configuration file. 
For example, if we want to run on Archer, in terminal we will execute:

``repex-amber --input='tsu_remd_ace_ala_nme.json' --rconfig='archer.json'``

**Note:** before using any of the resource configuration files for HPC clusters, please 
make appropriate changes to those files (as described in previous section).

Output verification is identical to the one described for the temperature exchange example. If simulation has successfully finished, one of the last lines of terminal log should be similar to:

.. parsed-literal::

    2015:10:11 18:49:59 6600   MainThread   radical.repex.amber   : [INFO    ] Simulation successfully finished!

NAMD example
=============

Now we will demonstrate how to run temperature exchange REMD simulation with NAMD engine.

**Note:** temperature exchange is the only REMD simulation type supported by RepEx. 

Temperature exchange (T-REMD) with deca-alanine helix
------------------------------------------------------

In RepEx examples directory for NAMD engine (``radical.repex/examples/namd``) are present the following files:

    ``t_remd_ala.json`` -- *simulation input file for temperature exchange using deca-alanine helix*  

    ``namd_inp`` -- *input files directory for temperature exchange simulations*

First we verify if parameters specified in ``t_remd_ala.json`` simulation input 
file satisfy our requirements. By default ``t_remd_ala.json`` file looks like this:

.. parsed-literal::

    {
        "remd.input": {
            "sync": "S",
            "number_of_cycles": "3",
            "input_folder": "namd_inp",
            "input_file_basename": "ala",
            "namd_structure": "ala.psf",
            "namd_coordinates": "unf.pdb",
            "namd_parameters": "ala.params",
            "steps_per_cycle": "1000"
        },
        "dim.input": {
            "d1": {
                "type" : "temperature",
                "number_of_replicas": "8",
                "min_temperature": "300.0",
                "max_temperature": "308.0"
            }
        }
    }

If we intend to run this example locally, the only **required** change is to add 
``"namd_path"`` parameter under ``"remd.input"`` key. If we use this simulation 
input file without any other changes, simulation will launch 8 replicas 
and will run 3 simulation cycles, while performing 1000 time-steps between exchanges. 

To run this example locally, in terminal we execute:

``repex-amber --input='t_remd_ala.json' --rconfig='local.json'``

To run this example on HPC cluster, we must specify appropriate resource configuration file. 
For example, if we want to run on Stampede, in terminal we will execute:

``repex-amber --input='t_remd_ala.json.json' --rconfig='stampede.json'``

**Note:** before using any of the resource configuration files for HPC clusters, please 
make appropriate changes to those files (as described in previous section).

If simulation has successfully finished, one of the last lines of terminal log should be similar to:

.. parsed-literal::

    2015:10:11 18:49:59 6600   MainThread   radical.repex.amber   : [INFO    ] Simulation successfully finished!

