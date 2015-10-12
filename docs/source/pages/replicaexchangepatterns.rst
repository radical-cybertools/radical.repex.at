.. _replicaexchangepatterns:

*************************
Replica Exchange Patterns
*************************

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

