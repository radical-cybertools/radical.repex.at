export RADICAL_REPEX_VERBOSE=info;
export RADICAL_PILOT_VERBOSE=info;
export REPEX_PROFILING=1;

repex-amber --input='tuu_remd_ace_ala_nme.json' --rconfig='local.json'

#repex-amber --input='sim.json' --rconfig='local.json'

#repex-amber --input='tuu_remd_phos_trans_qmmm.json' --rconfig='local.json'
