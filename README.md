#RepEx: Replica Exchange Molecular Dynamics simulations Package

RepEx is a novel Replica Exchange Molecular Dynamics (REMD)
simulations package for HPC clusters. The primary aim for the design of RepEx
is to decouple the implementation of the Replica Exchange (RE) algorithm from
the Molecular Dynamics (MD) simulation engine. Current version of RepEx supports Amber [1] and NAMD [2] simulation engines, and can be easily modified to support 
any other MD engine. 

RepEx supports multi-dimensional REMD simulations with arbitrary number and
ordering of dimensions. Currently RepEx supports three exchange types: salt
concentration, temperature and umbrella exchange. RepEx explicitly decouples the
number of replicas, from the computational resources (CPUs, GPUs, etc.). RepEx
can be used as a testing platform for new or unexplored REMD methods.

To execute its workloads, RepEx relies on the concept of task-level parallelism, which is enabled by the use of the RADICAL-Pilot API [Radical Pilot](http://radicalpilot.readthedocs.org/en/latest/).

RepEx supports synchronous and asynchronous RE patterns. Asynchronous RE
Pattern does not have a global synchronization barrier between simulation and
exchange phase. While some replicas are in the simulation phase, others might
be in the exchange phase. Based on some criterion, a subset of replicas
transition into the exchange phase, while other replicas continue in the
simulation phase. Selection of replicas that will transition may be based on a
FIFO principle, e.g. first N replicas transition into an exchange
phase. Alternatively, only replicas which have finished a predefined number of
simulation time-steps (2 ps) during some real time interval (1 minute)
transition into exchange phase.

[1] - [Amber](http://ambermd.org/)

[2] - [NAMD](http://www.ks.uiuc.edu/Research/namd/)

###User guide

RepEx user guide can be found at: [repex.readthedocs.org](http://repex.readthedocs.org/en/master/)

###Website

RepEx website can be found at: [repex.io](http://radical-cybertools.github.io/radical.repex/)

###ICPP-2016 paper

Paper in pdf format: [paper.pdf](https://github.com/radical-cybertools/radical.repex/blob/devel/documents/icpp16/paper.pdf)

Presentation in pdf format: [slides-icpp16.pdf](https://github.com/radical-cybertools/radical.repex/blob/devel/documents/icpp16/slides-icpp16.pdf)

###Presentations

A. Treikalis thesis: [at-thesis-slides.pdf](https://github.com/radical-cybertools/radical.repex/blob/devel/documents/presentations/at-thesis-slides.pdf)

Performance optimization slides: [repex-performance-optimization.pdf](https://github.com/radical-cybertools/radical.repex/blob/devel/documents/presentations/repex-performance-optimization.pdf)