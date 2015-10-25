export RADICAL_REPEX_VERBOSE=info;
export RADICAL_PILOT_VERBOSE=info;

#nohup repex-amber --input='tsu_remd_ace_ala_nme.json' --rconfig='stampede.json' 2> stampede.log

repex-amber --input='tuu_remd_ace_ala_nme.json' --rconfig='stampede.json'


#repex-amber --input='s_remd_ace_ala_nme.json' --rconfig='stampede.json'
#repex-amber --input='t_remd_ala10.json' --rconfig='archer.json'
