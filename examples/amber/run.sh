export RADICAL_PILOT_VERBOSE=DEBUG;
export SAGA_VERBOSE=INFO;
export RADICAL_PILOT_PROFILE=TRUE;
export SAGA_PTY_SSH_TIMEOUT=1000;

export RADICAL_REPEX_VERBOSE=info;
export RADICAL_PILOT_VERBOSE=debug;


# t_remd_ace_ala_nme.json
#repex-amber --input='amber_input.json' --rconfig='local.json'

repex-amber --input='t_remd_ace_ala_nme.json' --rconfig='local.json'
