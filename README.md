#RepEx: Replica Exchange simulations Package

RepEx is a new [Replica-Exchange](https://en.wikipedia.org/wiki/Parallel_tempering) Molecular Dynamics (REMD) simulations package 
written in Python programming language. RepEx supports Amber [1] and NAMD [2] as 
Molecular Dynamics application kernels and can be easily modified to support 
any conventional MD package. The main motivation behind RepEx is to enable 
efficient and scalable multi-dimensional replica-exchange MD (REMD) simulations on HPC systems, while separating 
execution details from simulation setup, specific to a given MD package. 
RepEx relies on a concept of Pilot-Job to run RE simulations on HPC 
clusters. RepEx is using [Radical Pilot](http://radicalpilot.readthedocs.org/en/latest/)
Pilot System for execution of  workloads. RepEx is modular, object-oriented code, 
which is designed to facilitate development of extension modules by it's users.

[1] - [Amber](http://ambermd.org/)

[2] - [NAMD](http://www.ks.uiuc.edu/Research/namd/)

###User guide

RepEx user guide can be found at: [repex.readthedocs.org](http://repex.readthedocs.org/en/latest/)

