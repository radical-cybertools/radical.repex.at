#!/bin/bash

now=`date '+%F_%H-%M-%S'`
cd test_results
mkdir test_$now
cd ..
#cd test_$now
file="output.txt"

echo "All produced output can be found in: " test_results/test_$now/$file
echo "Test harness for RepEx"  > test_results/test_$now/$file
echo "----------------------"  >> test_results/test_$now/$file

echo "========================================================================="  >> test_results/test_$now/$file
echo "Testing the availability of required tools for test suite." >> test_results/test_$now/$file
python --version &> /dev/null

  if (( $? == '0' )); then
      echo " python is available."  >> test_results/test_$now/$file
  else
      echo " FAIL: python not available: Exiting"   >> test_results/test_$now/$file
      exit 1
  fi

py.test --version &> /dev/null
  if (( $? == '0' )); then
      echo " pytest is available."  >> test_results/test_$now/$file
  else
      echo " FAIL: pytest not available: Exiting"   >> test_results/test_$now/$file
      exit 1
  fi

radicalpilot-version &> /dev/null
  if (( $? == '0' )); then
      echo " Radical-Pilot is available."  >> test_results/test_$now/$file
  else
      echo " FAIL: Radical-Pilot not available: Exiting"   >> test_results/test_$now/$file
      exit 1
  fi

repex-version &> /dev/null
  if (( $? == '0' )); then
      echo " RepEx is available."  >> test_results/test_$now/$file
  else
      echo " FAIL: RepEx not available: Exiting"   >> test_results/test_$now/$file
      exit 1
  fi



echo " " >> $file
echo "========================================================================="  >> test_results/test_$now/$file
echo "Executing Synchronous tests..."   >> test_results/test_$now/$file

#cd ../../patterns
echo " " >> $file
echo "Testing 1D for different input files"   >> test_results/test_$now/$file
echo "========================================================================="  >> test_results/test_$now/$file
#echo $pwd
py.test 1d/test_group_properties.py --cmdopt='sync/u_remd_ace_ala_nme.json'>> test_results/test_$now/$file
py.test 1d/test_group_properties.py --cmdopt='sync/t_remd_ace_ala_nme.json'>> test_results/test_$now/$file
py.test 1d/test_group_properties.py --cmdopt='sync/s_remd_ace_ala_nme.json'>> test_results/test_$now/$file


echo " " >> $file
echo "Testing 2D for different input files"   >> test_results/test_$now/$file
echo "========================================================================="  >> test_results/test_$now/$file
#echo $pwd
py.test 2d/test_group_properties.py --cmdopt='sync/st_remd_ace_ala_nme.json'>> test_results/test_$now/$file
py.test 2d/test_group_properties.py --cmdopt='sync/su_remd_ace_ala_nme.json'>> test_results/test_$now/$file
py.test 2d/test_group_properties.py --cmdopt='sync/ut_remd_ace_ala_nme.json'>> test_results/test_$now/$file


echo " " >> $file
echo "Testing 3D for different input files"   >> test_results/test_$now/$file
echo "========================================================================="  >> test_results/test_$now/$file
#echo $pwd
py.test 3d/test_group_properties.py --cmdopt='sync/stu_remd_ace_ala_nme.json'>> test_results/test_$now/$file
py.test 3d/test_group_properties.py --cmdopt='sync/sut_remd_ace_ala_nme.json'>> test_results/test_$now/$file
py.test 3d/test_group_properties.py --cmdopt='sync/suu_remd_ace_ala_nme.json'>> test_results/test_$now/$file
py.test 3d/test_group_properties.py --cmdopt='sync/tsu_remd_ace_ala_nme.json'>> test_results/test_$now/$file
py.test 3d/test_group_properties.py --cmdopt='sync/tus_remd_ace_ala_nme.json'>> test_results/test_$now/$file
py.test 3d/test_group_properties.py --cmdopt='sync/tuu_remd_ace_ala_nme.json'>> test_results/test_$now/$file
py.test 3d/test_group_properties.py --cmdopt='sync/usu_remd_ace_ala_nme.json'>> test_results/test_$now/$file
py.test 3d/test_group_properties.py --cmdopt='sync/utu_remd_ace_ala_nme.json'>> test_results/test_$now/$file
py.test 3d/test_group_properties.py --cmdopt='sync/uus_remd_ace_ala_nme.json'>> test_results/test_$now/$file
py.test 3d/test_group_properties.py --cmdopt='sync/uut_remd_ace_ala_nme.json'>> test_results/test_$now/$file



#echo " " >> $file
#echo "========================================================================="  >> $file
#echo "Test summary:"   >> $file
#echo "========================================================================="   >> $file

#if [ $testErr -eq 0 ]; then
#    echo "All done, API tests successful!"   >> $file
#else
#    echo $testErr "API test run error(s) encountered."  >> $file
#fi

#exit 0


