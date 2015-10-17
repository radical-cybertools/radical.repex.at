.. _introduction:

************
Introduction
************

What is RepEx ?
===============

RepEx is a new `Replica-Exchange <https://en.wikipedia.org/wiki/Parallel_tempering>`_ Molecular Dynamics (REMD) simulations package 
written in Python programming language. RepEx supports Amber [1] and NAMD [2] as 
Molecular Dynamics application kernels and can be easily modified to support 
any conventional MD package. The main motivation behind RepEx is to enable 
efficient and scalable multidimensional REMD simulations on HPC systems, while separating 
execution details from simulation setup, specific to a given MD package. 
RepEx provides several Execution Patterns designed to meet the needs of it's 
users. RepEx relies on a concept of Pilot-Job to run RE simulations on HPC 
clusters. Namely, RepEx is using `Radical Pilot <http://radicalpilot.readthedocs.org/en/latest/>`_
Pilot System for execution of it's workloads. RepEx effectively takes advantage 
of a task-level-parallelism concept to run REMD simulations. RepEx 
is modular, object-oriented code, which is designed to facilitate development of 
extension modules by it's users.

[1] - http://ambermd.org/

[2] - http://www.ks.uiuc.edu/Research/namd/


What can I do with it?
======================

Currently are supported the following one-dimentional REMD simulations: Temperature-Exchange (T-REMD), Umbrella Sampling (US-REMD) and Salt Concentration (S-REMD). It is possible to combine supported one-dimensional cases into multi-dimentional cases with arbitrary ordering and number of dimensions. This level of flexibility is not attainable by conventional MD software packages. RepEx easily can be used as a testing platform for new or unexplored REMD algorithms. Due to relative simplicity of the code, development time is significantly reduced, enabling scientists to focus on their experiments and not on a software engineering task at hand. 


Why should I use it?
====================

While many MD software packages provide implementations of REMD algorithms, a number of implementation challenges exist. Despite the fact that REMD algorithms are very well suited for parallelization, implementing dynamic pairwise communication between replicas is non-trivial. This results in REMD implementations being limited in terms of number of parameters being exchanged and being rigid in terms of synchronization mechanisms. 
The above challenges together with the limitations arising from design specifics contribute to scalability barriers in some MD software packages. For many scientific problems, simulations with number of replicas at the order of thousands would substantially improve sampling quality. 

Main distinguishing features of RepEx are:

 - low barrier for implementation of new REMD algorithms facilitated by separation of 
   simulaiton execuiton details from implementation specific to current MD package
   
 - functionality to run multi-dimentional REMD simulations with arbitrary ordering of dimensions

        