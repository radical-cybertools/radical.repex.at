#################################
# single-core replica experiments
#################################

virtualenv $HOME/ve; source $HOME/ve/bin/activate

mkdir repex-exp; cd repex-exp
wget https://pypi.python.org/packages/source/r/radical.pilot/radical.pilot-0.35.tar.gz
tar -zxvf radical.pilot-0.35.tar.gz
cd radical.pilot-0.35; pip install .
cd ..
git clone https://github.com/radical-cybertools/radical.repex.git
cd radical.repex; git checkout devel; python setup.py install
cd examples/amber

# to run on Stampede modify 'username', 'project, etc. in stampede.json:

{
    "target": {
        "resource": "xsede.stampede",
        "username" : "octocat",
        "project" : "TG-123456",
        "queue" : "development",
        "runtime" : "60",
        "cleanup" : "False",
        "cores" : "16"
    }
}

# to run on SuperMIC modify 'username', 'project, etc. in supermic.json:

{
    "target": {
        "resource": "xsede.supermic",
        "username" : "octocat",
        "project" : "TG-123456",
        "runtime" : "60",
        "cleanup" : "False",
        "cores" : "20"
    }
}

# to run TUU-REMD experiments modify tuu_remd_ace_ala_nme.json:

{
    "remd.input": {
        "re_pattern": "S",
        "exchange": "TUU-REMD",
        "number_of_cycles": "3",
        "input_folder": "tuu_remd_inputs",
        "input_file_basename": "ace_ala_nme_remd",
        "amber_input": "ace_ala_nme.mdin",
        "amber_parameters": "ace_ala_nme.parm7",
        "amber_coordinates_folder": "ace_ala_nme_coors",
        "same_coordinates": "True",
        "us_template": "ace_ala_nme_us.RST",
        "replica_gpu": "False",
        "replica_cores": "1",
        "steps_per_cycle": "500",
        "download_mdinfo": "False",
        "download_mdout" : "False"
        },
    "dim.input": {
        "umbrella_sampling_1": {
            "number_of_replicas": "4",
            "us_start_param": "0",
            "us_end_param": "360",
            "exchange_replica_cores" : "1",
            "exchange_replica_mpi": "False"
            },
        "temperature_2": {
            "number_of_replicas": "4",
            "min_temperature": "300",
            "max_temperature": "600",
            "exchange_replica_cores" : "1",
            "exchange_replica_mpi": "False"
            },
       
        "umbrella_sampling_3": {
            "number_of_replicas": "4",
            "us_start_param": "0",
            "us_end_param": "360",
            "exchange_replica_cores" : "1",
            "exchange_replica_mpi": "False"
            }    
    }
}

# to run TSU-REMD experiments modify tsu_remd_ace_ala_nme.json:

{
    "remd.input": {
        "re_pattern": "S",
        "exchange": "TSU-REMD",
        "number_of_cycles": "2",
        "input_folder": "tsu_remd_inputs",
        "input_file_basename": "ace_ala_nme_remd",
        "amber_input": "ace_ala_nme.mdin",
        "amber_parameters": "ace_ala_nme_old.parm7",
        "amber_coordinates_folder": "ace_ala_nme_coors",
        "same_coordinates" : "False",
        "us_template": "ace_ala_nme_us.RST",
        "replica_mpi": "False",
        "replica_cores": "1",
        "steps_per_cycle": "500",
        "exchange_off" : "False",
        "download_mdinfo": "False",
        "download_mdout" : "False"
        },
    "dim.input": {
        "temperature_1": {
            "number_of_replicas": "4",
            "min_temperature": "300",
            "max_temperature": "600"
            },
        "salt_concentration_2": {
            "number_of_replicas": "4",
            "exchange_replica_cores" : "4",
            "min_salt": "0.0",
            "max_salt": "1.0"
            },
        "umbrella_sampling_3": {
            "number_of_replicas": "4",
            "us_start_param": "0",
            "us_end_param": "360"
            }    
    }
}

# to run T-REMD experiments modify t_remd_ace_ala_nme.json,
# to run S-REMD experiments modify s_remd_ace_ala_nme.json,
# to run U-REMD experiments modify u_remd_ace_ala_nme.json.

# more info at: http://repex.readthedocs.org/en/master/

#################################
# multi-core replica experiments
#################################

virtualenv $HOME/ve; source $HOME/ve/bin/activate

mkdir repex-exp; cd repex-exp
wget https://pypi.python.org/packages/source/r/radical.pilot/radical.pilot-0.35.tar.gz
tar -zxvf radical.pilot-0.35.tar.gz
cd radical.pilot-0.35; pip install .
cd ..
git clone https://github.com/radical-cybertools/radical.repex.git
cd radical.repex; git checkout feature/experiments; python setup.py install
cd examples/amber

# to run on Stampede modify 'username', 'project, etc. in stampede.json:

{
    "target": {
        "resource": "xsede.stampede",
        "username" : "octocat",
        "project" : "TG-123456",
        "queue" : "development",
        "runtime" : "60",
        "cleanup" : "False",
        "cores" : "16"
    }
}

# to run on SuperMIC modify 'username', 'project, etc. in supermic.json:

{
    "target": {
        "resource": "xsede.supermic",
        "username" : "octocat",
        "project" : "TG-123456",
        "runtime" : "60",
        "cleanup" : "False",
        "cores" : "20"
    }
}

# to run TUU-REMD experiments modify tuu_remd_ace_ala_nme.json:

{
    "remd.input": {
        "re_pattern": "S",
        "exchange": "TUU-REMD",
        "number_of_cycles": "2",
        "input_folder": "tuu_remd_inputs",
        "input_file_basename": "ace_ala_nme_remd",
        "amber_input": "ace_ala_nme.mdin",
        "amber_parameters": "ace_ala_nme_big.parm7",
        "amber_coordinates_folder": "ace_ala_nme_big_coors",
        "same_coordinates": "True",
        "us_template": "ace_ala_nme_us.RST",
        "replica_mpi": "True",
        "replica_cores": "16",
        "steps_per_cycle": "1000",
        "download_mdinfo": "False",
        "download_mdout" : "False"
        },
    "dim.input": {
        "umbrella_sampling_1": {
            "number_of_replicas": "2",
            "us_start_param": "0",
            "us_end_param": "360",
            "exchange_replica_cores" : "1",
            "exchange_replica_mpi": "False"
            },
        "temperature_2": {
            "number_of_replicas": "2",
            "min_temperature": "300",
            "max_temperature": "600",
            "exchange_replica_cores" : "1",
            "exchange_replica_mpi": "False"
            },
       
        "umbrella_sampling_3": {
            "number_of_replicas": "2",
            "us_start_param": "0",
            "us_end_param": "360",
            "exchange_replica_cores" : "1",
            "exchange_replica_mpi": "False"
            }    
    }
}

# to run T-REMD experiments modify t_remd_ace_ala_nme.json:

{
    "remd.input": {
        "re_pattern": "S",
        "exchange": "T-REMD",
        "number_of_cycles": "2",
        "number_of_replicas": "8",
        "input_folder": "t_remd_inputs",
        "input_file_basename": "ace_ala_nme_remd",
        "amber_input": "ace_ala_nme.mdin",
        "amber_parameters": "ace_ala_nme_big.parm7",
        "amber_coordinates": "ace_ala_nme_big.inpcrd.0.0",
        "exchange_mpi": "True",
        "replica_mpi": "True",
        "replica_cores": "16",
        "min_temperature": "300",
        "max_temperature": "600",
        "steps_per_cycle": "20000",
        "download_mdinfo": "False",
        "download_mdout" : "False"
    }
}

# more info at: http://repex.readthedocs.org/en/master/


 
