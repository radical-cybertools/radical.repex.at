export RADICAL_REPEX_VERBOSE=info;
export RADICAL_PILOT_VERBOSE=info;
export REPEX_PROFILING=1;

#nohup repex-amber --input='tuu_remd_ace_ala_nme_test.json' --rconfig='stampede.json' 2> stampede.log &

nohup repex-amber --input='tsu_remd_dna_test.json' --rconfig='smic.json' 2> smic.log &

#repex-amber --input='tsu_remd_dna_new.json' --rconfig='local.json'

