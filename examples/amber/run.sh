export RADICAL_REPEX_VERBOSE=info;
export RADICAL_PILOT_VERBOSE=info;
export REPEX_PROFILING=1;
#unset RADICAL_PILOT_VERBOSE;

#nohup repex-amber --input='tsu_remd_ace_ala_nme.json' --rconfig='stampede.json' 2> stampede.log

#repex-amber --input='tsu_remd_ace_ala_nme.json' --rconfig='stampede.json'

nohup repex-amber --input='s_remd_ace_ala_nme.json' --rconfig='stampede.json' 2> stampede.log &

#repex-amber --input='t_remd_ala10.json' --rconfig='archer.json'
