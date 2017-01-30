.. _runningonhpcclusters:

***********************
Running on HPC clusters
***********************

In this section we will learn how to run RepEx examples on HPC clusters. 

**It is assumed that you have already installed RepEx, if not please go back to 
installation section**. 

To run examples with Amber MD engine, we must cd into Amber examples directory:

.. parsed-literal:: cd $HOME/radical.repex/examples/amber

To run examples with NAMD engine, we must cd into NAMD examples directory:

.. parsed-literal:: cd $HOME/radical.repex/examples/namd

In each of these directories are available resource configuration files, to run
simulations on the following HPC clusters:

    **Stampede** -- Texas Advanced Computing Center (resource tag ``xsede.stampede``)

    **SuperMIC** -- Louisiana State University (resource tag ``xsede.supermic``)

    **Blue Waters** -- National Center for Supercomputing Applications (resource tag ``ncsa.bw``)

    **Archer** -- Edinburgh Parallel Computing Centre (resource tag ``epsrc.archer``)

To run examples we must change the following parameters in a resource configuration file ``<resource-name>.json``:

    ``username`` -- *your username on target HPC cluster*

    ``project``  -- *your allocation on target HPC cluster*

    ``cores``    -- *number of CPU cores you would like to use for simulation*

    ``runtime``  -- *for how long you would like to run simulation (in minutes)*

In addition to these foru parameters we might want to add the following **optional** parameters:

    ``queue`` -- *specifies which queue to use for job submission (machine specific)*

    ``cleanup`` -- *specifies if files on remote machine must be deleted. Possible values are:* ``True`` *or* ``False``

    ``access_schema`` -- *access schema (more info at:* http://radicalpilot.readthedocs.io/en/latest/ *)*

    ``sandbox`` -- *working directory for this simulation on the file system of the target HPC cluster*

Example resource configuration file for SuperMIC is provided below:

.. parsed-literal::

    {
        "resource" : "xsede.supermic",
        "username" : "octocat",
        "project"  : "TG-XYZ123456",
        "runtime"  : "30",
        "cleanup"  : "False",
        "cores"    : "16"
    }

**Note:** we don't have to provide a path to Amber or NAMD executable on the target HPC clusters, 
since this is handled by RepEx. 