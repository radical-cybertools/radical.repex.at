.. _installation:

************
Installation
************

This page describes the requirements and procedure to be followed to install the
RepEx package.

   .. note:: Pre-requisites.The following are the minimal requirements to 
             install the RepEx package.

                * python >= 2.7
                * virtualenv >= 1.11
                * pip >= 1.5
                * Password-less access (ssh or gsissh) to target HPC cluster 

The easiest way to install RepEx is to create virtualenv. This way, RepEx and 
its dependencies can easily be installed in user-space without clashing with 
potentially incompatible system-wide packages.

.. tip:: If the virtualenv command is not available, try the following set of commands:

    .. parsed-literal:: wget --no-check-certificate https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.11.tar.gz
                        tar xzf virtualenv-1.11.tar.gz
                        python virtualenv-1.11/virtualenv.py --system-site-packages $HOME/ve/
                        source $HOME/ve/bin/activate

**Step 1** : Create and activate virtualenv:

.. parsed-literal:: virtualenv $HOME/ve/

.. parsed-literal:: source $HOME/ve/bin/activate

**Step 2** : Install RepEx:

.. parsed-literal:: pip install radical.repex

If installation was successful, you should be able to print the installed version of RepEx:

.. parsed-literal:: repex-version
                    0.2.10
