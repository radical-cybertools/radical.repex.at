export RADICAL_REPEX_VERBOSE=INFO;
export RADICAL_PILOT_VERBOSE=INFO;
export SAGA_VERBOSE=INFO;
#export RADICAL_VERBOSE=DEBUG; 
export REPEX_PROFILING=1;
export RADICAL_PILOT_PROFILE=TRUE;

nohup repex-amber --input='tuu_remd_ace_ala_nme.json' --rconfig='bw.json' 2> bw-tuu-sync-r512-c16448.log &


#repex-amber --input='tuu_remd_phos_trans_qmmm.json' --rconfig='local.json' 2> local.log &


