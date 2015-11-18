#!/bin/bash

for i in ace_ala_nme.inpcrd.7.*
do
mv ${i} ${i/inpcrd.7/inpcrd.14}
done
