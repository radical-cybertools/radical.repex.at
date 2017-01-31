export RADICAL_PILOT_VERBOSE=INFO;
export SAGA_VERBOSE=INFO;
export RADICAL_PILOT_PROFILE=TRUE;
export SAGA_PTY_SSH_TIMEOUT=1000;

nohup repex-amber --input='tuu_remd_ace_ala_nme.json' --rconfig='local.json' 2> local.log &

