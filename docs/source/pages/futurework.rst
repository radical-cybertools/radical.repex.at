.. _futurework:

***********
Preview 
***********

In this section we will describe some of the features, which have been developed but have not been released yet. They will be available in RepEx (as beta) in the very near future. 

Replica Exchange Patterns
=========================

A distinctive feature of RepEx is its ability to select a Replica Exchange (RE) Pattern. Replica Exchange Patterns differ in synchronization modes between MD and Exchange steps. We define two types of 
Replica Exchange Patterns:

 **1.** Synchronous Replica Exchange Pattern

 **2.** Asynchronous Replica Exchange Pattern

Synchronous Replica Exchange Pattern
------------------------------------

Synchronous RE Pattern, corresponds to the conventional way of running REMD simulations, where all replicas propagate MD for a fixed period of simulation time (e.g. 2 ps) before the exchange phase. The (physical) execution time for replicas is
not fixed, as all replicas must finish a fixed-number of MD-steps before the exchanges take place.

.. image:: ../figures/macro-pattern-a.png
	:alt: pattern-a
	:width: 7.0 in
	:align: center

Asynchronous Replica Exchange Pattern
-------------------------------------

In distinction to the Synchronous RE Pattern, the Asynchronous RE Pattern does not have a global synchronization 
barrier. While some replicas are performing an MD-step others might be performing an exchange amongst a subset of replicas. In the current implementation of Asynchronous RE Pattern, the MD phase is defined as a fixed period of simulation time (e.g. 2 ps), but the (physical) execution time for MD phase is fixed (e.g. wall-clock time of 30 secs). When the 
predefined physical execution time elapses, replicas which have finished adequate number of MD-steps transition into the exchange phase. In this pattern there is no synchronization between MD and Exchange phases, thus this pattern can be referred to as asynchronous.

.. image:: ../figures/macro-pattern-b.png
	:alt: pattern-a
	:width: 5.5 in
	:align: center


Flexible execution modes
========================

Depending upon the relative size of the resources available to the size of simulations (=number of replicas x resource requirement of each replica), Replica Exchange Patterns are executed differently. The details of the execution,
and in particular the resource management details, are captured by the concept of Execution Strategy. Importantly as an
end-user you do not have to worry about how these details are managed, but should be aware of how these modes differ:

 **1.** MD simulation time definition: fixed period of simulation time (e.g. 2 ps) 
 for all replicas or fixed period of wall clock time (e.g. 2 minutes) for all 
 replicas, meaning that after this time interval elapses all running replicas 
 will be stopped, regardless of how much simulation time was obtained.

 **2.** task submission modes (bulk submission vs sequential submission)

 **3.** task execution modes on remote HPC system (order and level of concurrency)

 **4.** number of Pilots used for a given simulation

 **5.** number of target resources used concurrently for a given simulation

Next we will introduce three Execution Strategies which can be used with Synchronous Replica 
Exchange Pattern.

Execution Mode S1
-----------------

Synchronous Replica Exchange simulations, may be executed using 
Execution strategy S1. This strategy differs from a conventional one in number of 
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
    :width: 7.5 in
    :align: center

Execution Mode S2
-----------------

Execution Strategy S2 differs from Strategy S1 in MD simulation time definition. 
Here MD is specified as a fixed period of wall clock time (e.g. 2 minutes) for 
all replicas. Replicas which will not finish MD-step within this time interval, 
will be stopped. In addition, Strategy S2 differs from Strategy S1 in the number 
of allocated cores. Here number of cores equals to the number of replicas.

.. image:: ../figures/exec-strategy-a2.png
    :alt: pattern-a
    :width: 6.5 in
    :align: center

Execution Mode S3
-----------------

Last Execution strategy we will discuss in this section is Execution Strategy S3. 
In this strategy all replicas are run concurrently for a presumably indefinite 
period. At predefined intervals exchanges are performed amongst all (or a subset) 
of replicas on resource using data from checkpoint files. Any replicas that accept
the exchange are reset and then restarted. Since only a small fraction of replicas 
will actually accept this exchange (∼10-30%) the amount of time discarded by the 
exchange is assumed to be minimal. Differences of this strategy from a conventional 
one can be attributed to bullet point **3.**

.. image:: ../figures/exec-strategy-a3.png
    :alt: pattern-a
    :width: 6.0 in
    :align: center

