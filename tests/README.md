# Testing for RepEx

##### Definition

- "1D Tests" (found in 1d/)
```
Test cases for 1-dimensional inputs. (Temperature, Salt Concentration and Unmbrella Sampling).
```
- "2D Tests" (found in 2d/)
```
Test cases for 2-dimensional inputs. Tests all possible pair combinations of Temperature, Salt 
Concentration and Unmbrella Sampling.
```
- "3D Tests" (found in 3d/)
```
Test cases for 3-dimensional inputs. Tests all the possible combination of 3 from Temperature,
Salt Concentration and Unmbrella Sampling.
```

##### Invocation

- To run synchronous tests:
```
./run_test_sync.sh
```

- To run asynchrounous tests:
```
./run_test_async.sh
```

- To run synchronous group tests:
```
./run_test_sync_g.sh
```

- To compare pairs\_for\_exchange file and simluation.pkl after each cycle (Successful only for 3D), run:
```
py.test 3D/test_compare.py --cmdopt='sync_g/tuu_remd_ace_ala_nme.json'
```
