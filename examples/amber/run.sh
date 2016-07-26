export RADICAL_REPEX_VERBOSE=INFO;
export RADICAL_PILOT_VERBOSE=INFO;
export SAGA_VERBOSE=INFO;
export REPEX_PROFILING=1;
export RADICAL_PILOT_PROFILE=TRUE;
export SAGA_PTY_SSH_TIMEOUT=500;

nohup repex-amber --input='t_remd_ace_ala_nme.json' --rconfig='smic.json' 2> smic-cross-sync-r40-c60-s6000-1.log &

