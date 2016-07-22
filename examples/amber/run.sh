export RADICAL_REPEX_VERBOSE=INFO;
export RADICAL_PILOT_VERBOSE=INFO;
export SAGA_VERBOSE=INFO;
export REPEX_PROFILING=1;
export RADICAL_PILOT_PROFILE=TRUE;
export SAGA_PTY_SSH_TIMEOUT=500;

nohup repex-amber --input='tuu_remd_phos_trans_qmmm.json' --rconfig='local.json' 2> local-qmmm-async-r8-c4.log &


#repex-amber --input='tuu_remd_phos_trans_qmmm.json' --rconfig='local.json' 2> local.log &


