##Installation instructions

One of the prerequisites for RepEx installation is Python version >= 2.7. You can check your Python version with:
```bash
python -V
```
If default Python version on your machine is below 2.7, you will need to install Python 2.7.x. More information on this can be found at:
```
https://www.python.org/download 
```
The first step in installing RepEx is to create and activate a fresh Python virtual environment:
```bash
virtualenv $HOME/myenv 
source $HOME/myenv/bin/activate
```
In case if virtual environment is not available on your machine, follow these instructions:
```bash
wget --no-check-certificate https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.10.tar.gz
tar xzf virtualenv-1.10.tar.gz
python virtualenv-1.10/virtualenv.py $HOME/myenv
source $HOME/myenv/bin/activate
```
Next you need to install radical-utils:
```bash
git clone -b devel https://github.com/radical-cybertools/radical.utils.git
cd radical.utils
python setup.py install
cd ..
```
After that saga-python must be installed:
```bash
pip install saga-python
```
or
```bash
easy_install saga-python
```
Next radical-pilot must be installed:
```bash
git clone https://github.com/radical-cybertools/radical.pilot.git
cd radical.pilot
python setup.py install
cd ..
```
Finally you can install RepEx:
```bash
git clone https://github.com/radical-cybertools/RepEx.git
cd RepEx
python setup.py install
```
Now you can verify that Radical Pilot was installed correctly:
```bash
radicalpilot-version
```
This should print Radical Pilot version in terminal
 
##Usage

Current version of RepEx code supports four RE schemes. Usage examples for for each scheme with each of the two supported MD kernels are provided in:
```
RepEx/examples/<kernel_name>/<scheme_nr> 
```
Before running any of the provided examples user must make appropriate changes to:
```
RepEx/examples/<kernel_name>/<scheme_nr>/config/<kernel_name>_input.json 
```
Instructions on how to modify <kernel_name>_input.json file to run simulation examples locally, on Gordon, Trestles and Stampede supercomputers are provided in:
```
RepEx/examples/<kernel_name>/<scheme_nr>/config/config.info
```    

####Usage example for scheme 1 with NAMD kernel


####Usage example for scheme 1 with Amber kernel


####Usage example for scheme 2 with NAMD kernel


####Usage example for scheme 2 with Amber kernel


####Usage example for scheme 2a with NAMD kernel


####Usage example for scheme 2a with Amber kernel


####Usage example for scheme 3 with NAMD kernel


####Usage example for scheme 3 with Amber kernel


####Usage example for scheme 4 with NAMD kernel


####Usage example for scheme 4 with Amber kernel



###Running simulation using RE scheme 2

To run RE simulation using scheme 2 and NAMD kernel in namd_input.json "number_of_replicas" must be greater than "cores". As mentioned previously recommended "cores" value is 50% of the "number_of_replicas". Similarly to scheme 1 two options with respect to exchange step are available. For RE simulation with remote exchange step in terminal execute: 
```bash
python launch_simulation_scheme_2_namd.py --input='config/namd_input.json'
```
For RE simulation with local exchange step in terminal execute:
```bash
python launch_simulation_scheme_2a_namd.py --input='config/namd_input.json'
``` 
After simulation is done, please verify existance of the output files in "replica_x" directories.


To run RE simulation using scheme 2 and Amber kernel you will need to modify amber_input.json file so that "number_of_replicas" is less than "cores". For RE simulation with remote exchange step in terminal execute: 
```bash
python launch_simulation_scheme_2_amber.py --input='config/amber_input.json'
```
For RE simulation with local exchange step in terminal execute:
```bash
python launch_simulation_scheme_2a_amber.py --input='config/amber_input.json'
``` 

###Running simulation using RE scheme 3

For this scheme it is recommended to add a key-value pair <"cycle_time": "integer_value"> to "input.MD" dictionary in <kernel_name>_input.json file. Value of "cycle_time" specifies wall clock time in minutes, which represents simulation cycle. If this key-value pair is not added default value of 1 minute will be used. Generally while changing "number_of_replicas" users will also need to adjust the value of "cycle_time", in order to maximize the number of replicas participating in each exchange step. After all changes (including those specified in /src/radical/repex/config/config.info file) are performed RE simulation can be launched using commands specified below.    

To run RE simulation using scheme 3 and NAMD kernel the following command must be executed in terminal:
```bash
python launch_simulation_scheme_3_namd.py --input='config/namd_input.json'
```  
To run RE simulation using scheme 3 and Amber kernel run:
```bash
python launch_simulation_scheme_3_amber.py --input='config/amber_input.json'
``` 
After simulation is done, please verify existance of the output files in "replica_x" directories.


###Troubleshooting

If your simulation fails for some reason the first thing to do is to re-run it with verbose flag:


```bash
RADICAL_PILOT_VERBOSE=info python <launcher_name>.py --input='config/<input_file>.json'
```

This will give you substantially more information about what is happening "under the bonnet" of the application. 