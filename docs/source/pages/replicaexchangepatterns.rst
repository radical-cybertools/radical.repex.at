.. _replicaexchangepatterns:

*************************
Replica Exchange Patterns
*************************

One of the distinctive features that RepEx provides to its users, is ability to
select a Replica Exchange Pattern. Replica Exchange Patterns differ in 
synchronization modes between MD and Exchange steps. We define two types of 
Replica Exchange Patterns:

 **1.** Synchronous Replica Exchange Pattern

 **2.** Asynchronous Replica Exchange Pattern

Synchronous Replica Exchange Pattern
------------------------------------

Synchronous Pattern, corresponds to conventional way of
running REMD simulations, where all replicas propagate MD for a
fixed period of simulation time (e.g. 2 ps) and execution time for replicas is
not fixed - all replicas must finish MD-step before Exchange-step takes place.
When all replicas have finished MD-step, the Exchange-step is performed. 

.. image:: ../figures/macro-pattern-a.png
	:alt: pattern-a
	:width: 7.0 in
	:align: center

Asynchronous Replica Exchange Pattern
-------------------------------------

Contrary to Synchronous Pattern, Asynchronous Pattern does not have a global synchronization 
barrier - while some replicas are performing an MD-step others might be performing an Exchange-step amongst a subset of replicas. In current implementation of Asynchronous Pattern, MD-step is defined as a fixed period of simulation time (e.g. 2 ps), but execution time for MD-step is fixed (e.g. 30 secs). Then
predefined execution time elapses, Exchange-step is performed amongst replicas
which have finished MD-step. In this pattern there is no synchronization between
MD and Exchange-step, thus this pattern can be referred to as asynchronous.

.. image:: ../figures/macro-pattern-b.png
	:alt: pattern-a
	:width: 5.5 in
	:align: center

