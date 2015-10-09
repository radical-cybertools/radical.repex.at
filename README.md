#RepEx: Replica Exchange simulations Package

RepEx is a new `Replica-Exchange <https://en.wikipedia.org/wiki/Parallel_tempering>`_ Molecular Dynamics (REMD) simulations package 
written in Python programming language. RepEx supports Amber [1] and NAMD [2] as 
Molecular Dynamics application kernels and can be easily modified to support 
any conventional MD package. The main motivation behind RepEx is to enable 
efficient and scalable multidimensional REMD simulations on HPC systems, while separating 
execution details from simulation setup, specific to a given MD package. 
RepEx relies on a concept of Pilot-Job to run RE simulations on HPC 
clusters. Namely, RepEx is using `Radical Pilot <http://radicalpilot.readthedocs.org/en/latest/>`_
Pilot System for execution of it's workloads. RepEx is modular, object-oriented code, 
which is designed to facilitate development of extension modules by it's users.


###User guide

RepEx user guide can be found at: [http://repex.readthedocs.org/en/devel-antons/]

