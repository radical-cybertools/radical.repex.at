export RADICAL_REPEX_VERBOSE=info;
export RADICAL_PILOT_VERBOSE=info;

nohup repex-namd --input='t_remd_ala.json' --rconfig='local.json' 2> local.log &

