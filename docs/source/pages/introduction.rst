.. _introduction:

Introduction
============

What is Repex ?
----------------

RepEx is a flexible Python package which is aimed at enabling users to perform 
Replica Exchange Molecular Dynamics (REMD) simulations at scale. RepEx relies on 
a concept of Pilot Job to run RE simulation on HPC clusters and Grids. Namely, 
RepEx is using `Radical Pilot <http://radicalpilot.readthedocs.org/en/latest/>`_
Pilot System for execution of it's workloads. Currently RepEx supports two MD 
packages as it's application kernels - Amber and MAND. Each of these MD kernels 
can be used to run REMD simulation conforming to one of three currently 
supported RE schemes. RepEx is modular object-oriented code, which is designed 
to facilitate development of extension modules by it's users.

[1] - http://ambermd.org/ 
[2] - http://www.ks.uiuc.edu/Research/namd/
