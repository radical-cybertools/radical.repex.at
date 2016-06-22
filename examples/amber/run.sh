export RADICAL_REPEX_VERBOSE=INFO;
export RADICAL_PILOT_VERBOSE=DEBUG;
export SAGA_VERBOSE=DEBUG;
export RADICAL_VERBOSE=DEBUG; 
export REPEX_PROFILING=1;
export RADICAL_PILOT_PROFILE=TRUE;

#nohup repex-amber --input='tuu_remd_ace_ala_nme_test.json' --rconfig='stampede.json' 2> stampede.log &

#nohup repex-amber --input='tuu_remd_ace_ala_nme.json' --rconfig='local.json' 2> local.log &

#repex-amber --input='t_remd_ace_ala_nme.json' --rconfig='stampede.json'

repex-amber --input='tuu_remd_phos_trans_qmmm.json' --rconfig='local.json' 2> local.log &


