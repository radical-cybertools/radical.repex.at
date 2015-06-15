#!/bin/bash

# this script should be executed in the rp session directory on remote cluster
# after executing the script, look in to the replica_*.log files and see if there's exchange (if parameter changes during simulation)
# does not guarantee correctness even if there're exchanges, could be used as a quick check however

rm replica_*.log

for ((i=0; i<=63; i++))  # number of replicas 64
do
  touch replica_$i.log
  for ((j=0; j<=23; j++))  # number of finished cycles 24
  do
    echo Cycle_$j >> replica_$i.log
    grep temp0 */ace_ala_nme_remd_${i}_${j}.mdin >> replica_$i.log
    grep DISANG */ace_ala_nme_remd_${i}_${j}.mdin >> replica_$i.log
  done
done

for f in replica_*.log
do
  sed -i '1,$s/  nstlim = 6000, dt = 0.001, temp0 = /Temperature = /' $f  # somehow hardcoded for the alanine dipeptide test case
  sed -i '1,$s/ DISANG=ace_ala_nme_us.RST./Umbrella Index= /' $f
done
