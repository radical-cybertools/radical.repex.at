.. _replicaexchangepatterns:

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
she would use ``repex-amber`` command line tool. In addiiton to specifying an 
appropriate command line tool, user need to specify a resource configuration file 
and REMD simulation input file. the result invocation of RepEx should be:

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

Execution Patterns
==================

One of the distinctive features that RepEx provides to its users, is ability to
select an Execution Pattern. An Execution Pattern is the set of configurations,
sequence and specific details of synchronization for a given REMD simulation.  
Execution Patterns formalize the set of decisions taken to execute REMD 
simulation, exposing certain variables and constraining some decisions.

Execution Patterns are fully specified by two sub-categories: Replica Exchange
Patterns and Execution Strategies. 

Replica Exchange Patterns
=========================

Replica Exchange Patterns are distinguished by synchronization modes between MD 
and Exchange steps. We define two types of Replica Exchange Patterns:

 **1.** Synchronous Pattern (Replica Exchange Pattern A)

 **2.** Asynchronous Pattern (Replica Exchange Pattern B)

Replica Exchange Pattern A
--------------------------

Pattern A, corresponds to conventional, synchronous way of
running REMD simulation, where all replicas propagate MD for a
fixed period of simulation time (e.g. 2 ps) and execution time for replicas is
not fixed - all replicas must finish MD-step before Exchange-step takes place.
When all replicas have finished MD-step, the Exchange-step is performed. 

.. image:: ../figures/macro-pattern-a.png
	:alt: pattern-a
	:height: 4.5 in
	:width: 7.0 in
	:align: center

Replica Exchange Pattern B
--------------------------

Contrary to Pattern A, Pattern B has execution related invariant: the number of
replicas must exceed allocated CPU cores so that only a fraction of replicas can
run. In Pattern B, MD-step is defined as a fixed period of simulation time
(e.g. 2 ps), but execution time for MD-step is fixed (e.g. 30 secs). Then
predefined execution time elapses, Exchange-step is performed amongst replicas
which have finished MD-step. In this pattern there is no synchronization between
MD and Exchange-step, thus this pattern can be referred to as asynchronous.

.. image:: ../figures/macro-pattern-b.png
	:alt: pattern-a
	:height: 4 in
	:width: 5.5 in
	:align: center

Execution Strategies
====================

Execution Strategies specify workload execution details and in particular
the resource management details. These strategies differ in: 

 **1.** MD simulation time definition: fixed period of simulation time (e.g. 2 ps) 
 for all replicas or fixed period of wall clock time (e.g. 2 minutes) for all 
 replicas, meaning that after this time interval elapses all running replicas 
 will be stopped, regardless of how much simulation time was obtained.

 **2.** task submission modes (bulk submission vs sequential submission)

 **3.** task execution modes on remote HPC system (order and level of concurrency)

 **4.** number of Pilots used for a given simulation

 **5.** number of target resources used concurrently for a given simulation

Next we will introduce three Execution Strategies which can be used with Replica 
Exchange Pattern A.

Execution Strategy A1
--------------------- 

Simulation corresponding to Replica Exchange Pattern A, may be executed using 
Execution strategy A1. This strategy differs from a conventional one in number of 
allocated cores on a target resource (bullet point **3.**). In this case number of 
cores is 1/2 of the number of replicas. As a result of this, 
only a half of replicas can propogate MD or Exchange-step concurrently. In this 
execution strategy MD simulation time is defined as a fixed period of simulation 
time (e.g. 2 ps) for all replicas, meaning that replicas which will finish simulation 
earlier will have to wait for other replicas before exchange-step may take place.
This strategy demonstrates advantage of using a task-level parallelism based 
approach. Many MD packages are lacking the capability to use less cores than replicas.     

.. image:: ../figures/exec-strategy-a1.png
    :alt: pattern-a
    :height: 5.0 in
    :width: 7.5 in
    :align: center

Execution Strategy A2
---------------------

Execution Strategy A2 differs from Strategy A1 in MD simulation time definition. 
Here MD is specified as a fixed period of wall clock time (e.g. 2 minutes) for 
all replicas. Replicas which will not finish MD-step within this time interval, 
will be stopped. In addition, Strategy A2 differs from Strategy A1 in the number 
of allocated cores. Here number of cores equals to the number of replicas.

.. image:: ../figures/exec-strategy-a2.png
    :alt: pattern-a
    :height: 4.5 in
    :width: 6.5 in
    :align: center

Execution Strategy A3
---------------------

Last Execution strategy we will discuss in this section is Execution Strategy A3. 
In this strategy all replicas are run concurrently for a presumably indefinite 
period. At predefined intervals exchanges are performed amongst all (or a subset) 
of replicas on resource using data from checkpoint files. Any replicas that accept
the exchange are reset and then restarted. Since only a small fraction of replicas 
will actually accept this exchange (∼10-30%) the amount of time discarded by the 
exchange is assumed to be minimal. Differences of this strategy from a conventional 
one can be attributed to bullet point **3.**

.. image:: ../figures/exec-strategy-a3.png
    :alt: pattern-a
    :height: 4.5 in
    :width: 6.0 in
    :align: center