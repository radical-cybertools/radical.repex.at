export RADICAL_PILOT_VERBOSE=INFO;
export SAGA_VERBOSE=INFO;
export RADICAL_PILOT_PROFILE=TRUE;
export SAGA_PTY_SSH_TIMEOUT=1000;

nohup repex-amber --input='t_remd_ala10.json' --rconfig='local.json' 2> local.log &
