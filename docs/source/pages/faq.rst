.. _faq:

***************************
Frequently Asked Questions
***************************

Where are .mdout files?
------------------------

If you want to get .mdout files downloaded back to your laptop, in simulation 
input file you must specify: ``"download_mdout": "True"``. Once simulation is done, 
in ``simulation_output`` directory you will find .mdout files for each MD simulation 
cycle performed by each replica.

Where are .mdinfo files?
-------------------------

If you want to get .mdinfo files downloaded back to your laptop, in simulation 
input file you must specify: ``"download_mdinfo": "True"``. Once simulation is done, 
in ``simulation_output`` directory you will find .mdinfo files for each MD simulation 
cycle performed by each replica.

How can I obtain information about accepted exchanges?
-------------------------------------------------------

If you want to check which replicas exchanged parameters after each cycle, 
you can examine ``pairs_for_exchange_d_c.dat`` files. these file are available in 
``simulation_output`` directory after simulation has finished. In these files are 
recorded indexes of replicas which exchanged parameters after given cycle.

        