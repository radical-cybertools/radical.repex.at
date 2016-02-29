export RADICAL_REPEX_VERBOSE=info;
export RADICAL_PILOT_VERBOSE=info;
export REPEX_PROFILING=1;
#unset RADICAL_PILOT_VERBOSE;

repex-amber --input='simulation_input.json' --rconfig='local.json'

#nohup repex-amber --input='s_remd_ace_ala_nme.json' --rconfig='smic.json' 2> smic_salt_64_6000.log &

#nohup repex-amber --input='s_remd_ace_ala_nme.json' --rconfig='smic.json' 2> smic_64.log &

#nohup repex-amber --input='s_remd_ace_ala_nme.json' --rconfig='smic.json' 2> smic_1000_1.log &

#repex-amber --input='t_remd_ala10.json' --rconfig='archer.json'

#repex-amber --input='tsu_remd_dna_gold.json' --rconfig='stamp.json'
