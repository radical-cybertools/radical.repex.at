export RADICAL_REPEX_VERBOSE=info;
export RADICAL_PILOT_VERBOSE=debug;

#python launch_simulation_pattern_b.py --input='amber_input.json'

repex-amber --input='amber_input.json' --rconfig='stampede.json'

#nohup python launch_simulation_pattern_b.py --input='amber_input.json' 2> log.1 &
