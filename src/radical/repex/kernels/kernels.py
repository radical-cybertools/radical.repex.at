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
                "pre_execution" : ["module load TACC", "module load amber/12.0"],
                "executable" : "/opt/apps/intel13/mvapich2_1_9/amber/12.0/bin/sander.MPI"
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
    },"trestles.sdsc.xsede.org":
    {
        "params":
        {
            "cores": 32,
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
                "pre_execution" : ["module load amber/14"],
                "executable" : "/opt/amber/bin/sander.MPI"
            }
        }
    },"gordon.sdsc.xsede.org":
    {
        "params":
        {
            "cores": 32,
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
                "pre_execution" : ["module load amber/14"],
                "executable" : "/opt/amber/bin/sander.MPI"
            }
        }
    },"localhost.linux.x86":
    {
        "params":
        {
            "cores": 2,
        },
        "kernels":
        {
            "namd": {
                "environment" : {},
                "pre_execution" : [],
                "executable" : "../../../../../NAMD_2.9_Linux-x86/namd2"
            }
        }
    },"localhost.linux.x86.64":
    {
        "params":
        {
            "cores": 2,
        },
        "kernels":
        {
            "namd": {
                "environment" : {},
                "pre_execution" : [],
                "executable" : "../../../../../NAMD_2.9_Linux-x86_64/namd2"
            }
        }
    },"localhost.macos.x86":
    {
        "params":
        {
            "cores": 2,
        },
        "kernels":
        {
            "namd": {
                "environment" : {},
                "pre_execution" : [],
                "executable" : "../../../../../NAMD_2.9_MacOSX-x86-multicore/namd2"
            }
        }
    },"localhost.macos.x86":
    {
        "params":
        {
            "cores": 2,
        },
        "kernels":
        {
            "namd": {
                "environment" : {},
                "pre_execution" : [],
                "executable" : "../../../../../NAMD_2.9_MacOSX-x86-multicore/namd2"
            }
        }
    },"localhost.macos.x86.64":
    {
        "params":
        {
            "cores": 2,
        },
        "kernels":
        {
            "namd": {
                "environment" : {},
                "pre_execution" : [],
                "executable" : "../../../../../NAMD_2.9b3_MacOSX-x86_64-multicore/namd2"
            }
        }
    }
}
