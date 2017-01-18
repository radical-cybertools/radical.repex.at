.. _faq:

***************************
Frequently Asked Questions
***************************

Where are .mdout files?
------------------------

If you want to get .mdout files downloaded back to your laptop, in REMD simulation 
input file you must specify: ``"download_mdout": "True"``. Once simulation is done, 
in replica_x durectories you will find .mdout files for each simulation run performed 
by this replica.

Where are .mdinfo files?
-------------------------

If you want to get .mdinfo files downloaded back to your laptop, in REMD simulation 
input file you must specify: ``"download_mdinfo": "True"``. Once simulation is done, 
in replica_x durectories you will find .mdinfo files for each simulation run performed 
by this replica.

How can I obtain information about accepted exchanges?
-------------------------------------------------------

If you want to check which replicas exchanged configurations during each cycle 
you can cd into ``shared_files`` directory and check each of four ``pairs_for_exchange_d_c.dat`` files. In these files are recorded indexes of replicas exchanging configurations during each cycle.

        