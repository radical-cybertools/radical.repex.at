export RADICAL_REPEX_VERBOSE=INFO;
export RADICAL_PILOT_VERBOSE=INFO;
export SAGA_VERBOSE=INFO;
export REPEX_PROFILING=1;
export RADICAL_PILOT_PROFILE=TRUE;
export SAGA_PTY_SSH_TIMEOUT=500;

#nohup repex-amber --input='t_remd_ace_ala_nme.json' --rconfig='smic.json' 2> smic-tremd-async-r40-c40-a888-s6000.log &


nohup repex-amber --input='tuu_remd_phos_trans_qmmm.json' --rconfig='stampede.json' 2> stamp-sync-r64-c64-sleep30-ex.log &


