#!/bin/bash -l

# Change to working directory for unit
cd /home/antontre/radical.pilot.sandbox/rp.session.ip-10-184-31-85.treikalis.016577.0001-pilot.0000/unit.000014
# Pre-exec commands
module load amber/14
# The command to run
python "amber_matrix_calculator_2d_pattern_b.py" "{\"init_temp\": \"600.0\", \"replicas\": \"4\", \"amber_parameters\": \"../staging_area/ala10.prmtop\", \"all_salt_ctr\": [\"0.0\", \"1.0\", \"0.0\", \"1.0\"], \"r_old_path\": \"\", \"all_temp\": [\"300.0\", \"300.0\", \"600.0\", \"600.0\"], \"replica_cycle\": \"1\", \"base_name\": \"ala10_remd\", \"amber_path\": \"/opt/amber/bin/sander\", \"amber_input\": \"ala10.mdin\", \"replica_id\": \"2\"}"
