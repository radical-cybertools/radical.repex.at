export RADICAL_REPEX_VERBOSE=info;
export RADICAL_PILOT_VERBOSE=info;
export REPEX_PROFILING=1;

#nohup repex-amber --input='tuu_remd_ace_ala_nme_test.json' --rconfig='stampede.json' 2> stampede.log &

#nohup repex-amber --input='tuu_remd_phos_trans_qmmm.json' --rconfig='stampede.json' 2> 512-async-stamp-1000.log &

repex-amber --input='t_remd_ace_ala_nme.json' --rconfig='stampede.json'

#repex-amber --input='tuu_remd_phos_trans_qmmm.json' --rconfig='local.json'


