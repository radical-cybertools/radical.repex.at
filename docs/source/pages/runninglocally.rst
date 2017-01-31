.. _runninglocally:

***************
Running locally 
***************

In this section we will describe how to run REMD simulations with RepEx on your 
workstation or laptop. 

**It is assumed that you have already installed RepEx, if not please go back to 
installation section**.


Preparation
===========

To obtain simulation input files we clone RepEx repository:

.. parsed-literal:: cd $HOME; git clone https://github.com/radical-cybertools/radical.repex.git

Next we **cd** into directory where input files recide. For Amber examples:

.. parsed-literal:: cd $HOME/radical.repex/examples/amber

For NAMD examples:

.. parsed-literal:: cd $HOME/radical.repex/examples/namd

Amongst other things in examples directory exists:

    ``local.json`` -- resource configuration file for running simulations on 
    your workstation

We now make appropriate changes to ``local.json`` resouce configuration 
file. We open this file in our favorite text editor (``vim`` in this case):

.. parsed-literal:: vim local.json

By default this file looks like this:

.. parsed-literal::

    {
        "target": {
            "resource": "local.localhost",
            "username" : "octocat",
            "runtime" : "30",
            "cleanup" : "False",
            "cores" : "4"
        }
    }

We need to modify three parameters in this file:

    ``username`` -- this should be your username on your workstation

    ``cores`` -- change this parameter to the number of cores supported by your workstation

    ``mongo_url`` -- url to your local **MongoDB** instance, for example ``"mongodb://localhost:27017/repex-examples"``

To run examples you will need to install **MongoDB** on your workstation, 
or if you have access to a virtual machine with already installed **MongoDB** 
instance you can use it as well.

Installing and configuring **MongoDB** is a straightforward process, which should 
not take more than ~5 minutes. Instalation instructions are provided at: ``https://docs.mongodb.com/manual/installation/``

**Note:** After you will launch your first simulation, in your ``$HOME`` directory 
will be created ``radical.pilot.sandbox`` directory. In this sandbox, for each 
simulation you will launch will be created a separate directory named ``rp.session.xxx``, 
where ``xxx`` is a character sequence specific to your simulation.

Amber examples
===============

For Amber MD engine RepEx supports exchange of three different parameters:

    **temperature exchange**

    **umbrella exchange**

    **salt concentration exchange** 

These exchange parameters can be combined into a **multi-dimensional** simulation, 
with arbitrary ordering of exchanges of these parameters. In RepEx **version 2.10** 
up to **three dimensions** are supported, but this limitation is artificial.    

To run examples with Amber engine you **must** have Amber installed on your 
workstation. If you don't have Amber installed please download it from: ``http://ambermd.org/antechamber/download.html`` and install it using instructions provided at: ``http://ambermd.org/`` 

For each example, in **simulation input file** we will need to specify a path to 
``sander`` executable, which is located on your workstation. This should be done by adding ``amber_path`` parameter under ``remd.input`` key in **simulation input file** we intend to use to run a given example:

.. parsed-literal:: "amber_path": "/home/octocat/amber/amber14/bin/sander"


NAMD examples
==============

For NAMD MD engine are supported only **temperature exchange** REMD simulations.

To run examples with NAMD engine you **must** have NAMD available on your 
workstation. If you don't have NAMD on your workstation, please download and 
install it using instructions provided at: ``http://www.ks.uiuc.edu/Research/namd/``

For each example, in **simulation input file** we will need to specify a path to 
``namd2`` executable, which is localted on your workstation. This should be done by adding ``namd_path`` parameter under ``remd.input`` key in **simulation input file** we intend to use to run a given example:

.. parsed-literal:: "namd_path": "/home/octocat/NAMD_2.9_Linux-x86/namd2"

