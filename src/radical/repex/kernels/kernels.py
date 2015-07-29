""" Application kernel configuration file.
"""

KERNELS = {

    "stampede.tacc.utexas.edu":
    {
        "params":
        {
            "cores": 16,
        },
        "kernels":
        {
            "amber": {
                "environment" : {},
                "pre_execution" : ["module restore", "module load amber", "module load python"],
                "executable" : "/opt/apps/intel13/mvapich2_1_9/amber/12.0/bin/sander",
                "executable_mpi" : "/opt/apps/intel13/mvapich2_1_9/amber/12.0/bin/sander.MPI"

            },
            "namd": {
                "environment" : {},
                "pre_execution" : ["module load TACC", "module load namd/2.9"],
                "executable" : "/opt/apps/intel13/mvapich2_1_9/namd/2.9/bin/namd2"
            }
        }
    },"archer.ac.uk":
    {
        "params":
        {
            "cores": 24,
        },
        "kernels":
        {
            "amber": {
                "environment" : {},
                "pre_execution" : ["module load amber/12"],
                "executable" : "/work/y07/y07/amber/12/bin/sander.MPI"
            }
        }
    },"gordon.sdsc.xsede.org":
    {
        "params":
        {
            "cores": 16,
        },
        "kernels":
        {
            "namd": {
                "environment" : {},
                "pre_execution" : ["module load namd/2.9"],
                "executable" : "/opt/namd/bin/namd2"
            },
            "amber": {
                "environment" : {},
                "pre_execution" : ["module load python", "module load amber"],
                "executable" : "/opt/amber/bin/sander",
                "executable_mpi" : "/opt/amber/bin/sander.MPI"
            }
        }
    },"local.localhost":
    {
        "params":
        {
            "cores": 1,
        },
        "kernels":
        {
            "amber": {
                "pre_execution" : [],
                "executable" : "/home/antons/amber/amber14/bin/sander",
                "executable_mpi" : "/home/antons/amber/amber14/bin/sander"
            }
        }
    }
}
