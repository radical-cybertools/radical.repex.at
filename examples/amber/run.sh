export RADICAL_REPEX_VERBOSE=info;
export RADICAL_PILOT_VERBOSE=info;

repex-amber --input='t_remd_ace_ala_nme.json' --rconfig='stampede.json'
#repex-amber --input='us_remd_ace_ala_nme.json' --rconfig='stampede.json'
#repex-amber --input='s_remd_ace_ala_nme.json' --rconfig='stampede.json'

#repex-amber --input='t_remd_ala10.json' --rconfig='archer.json'
