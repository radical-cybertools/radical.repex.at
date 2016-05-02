export RADICAL_REPEX_VERBOSE=info;
export RADICAL_PILOT_VERBOSE=info;
export REPEX_PROFILING=1;

nohup repex-amber --input='tsu_remd_dna_new.json' --rconfig='stampede.json' 2> tsu-1.log &

#repex-amber --input='tsu_remd_dna_new.json' --rconfig='local.json'

