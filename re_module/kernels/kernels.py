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
                "pre_execution" : "module load TACC && module load amber/12.0",
                "executable" : "/opt/apps/intel13/mvapich2_1_9/amber/12.0"
            },
            "namd": {
                "environment" : {},
                "pre_execution" : "module load TACC && module load namd/2.9",
                "executable" : "/opt/apps/intel13/mvapich2_1_9/namd/2.9/bin/namd2"
            }
        }
    },"localhost:local":
    {
        "params":
        {
            "cores": 2,
        },
        "kernels":
        {
            "namd": {
                "environment" : {},
                "pre_execution" : {},
                "executable" : "../../../NAMD_2.9_Linux-x86/namd2"
            }
        }
    }
}
