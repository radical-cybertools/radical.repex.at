import unittest
import os
import os.path
import json

PWD = os.path.dirname(os.path.abspath(__file__))

class TestInput(unittest.TestCase):

    def test_folder_existance(self):
        json_data=open("../re_module/config/input.json")
        inp_file = json.load(json_data)
        json_data.close()

        inp_folder = inp_file['input.NAMD']['input_folder']
        path = PWD[:-5] + "re_module/" + inp_folder
        
        # test if input folder exists
        self.assertTrue( os.path.exists(path) )

    def test_file_existance(self):
        json_data=open("../re_module/config/input.json")
        inp_file = json.load(json_data)
        json_data.close()

        inp_folder = inp_file['input.NAMD']['input_folder']
        namd_structure = inp_file['input.NAMD']['namd_structure']
        namd_coordinates = inp_file['input.NAMD']['namd_coordinates']
        namd_parameters = inp_file['input.NAMD']['namd_parameters']
        path = PWD[:-5] + "re_module/" + inp_folder + "/"

        # test if namd structure file exists 
        self.assertTrue( os.path.isfile(path + namd_structure) )

        # test if namd coordinates file exists 
        self.assertTrue( os.path.isfile(path + namd_coordinates) )

        # test if namd parameters file exists 
        self.assertTrue( os.path.isfile(path + namd_parameters) )

    def test_file_extensions(self):
        json_data=open("../re_module/config/input.json")
        inp_file = json.load(json_data)
        json_data.close()

        namd_structure = inp_file['input.NAMD']['namd_structure']
        namd_coordinates = inp_file['input.NAMD']['namd_coordinates']
        namd_parameters = inp_file['input.NAMD']['namd_parameters']

        # test file extensions for namd input files
        self.assertTrue( namd_structure[-3:] == "psf" )
        self.assertTrue( namd_coordinates[-3:] == "pdb" )
        self.assertTrue( namd_parameters[-6:] == "params" )

    def test_temperature(self):
        json_data=open("../re_module/config/input.json")
        inp_file = json.load(json_data)
        json_data.close()

        min_temp = float(inp_file['input.NAMD']['min_temperature'])
        max_temp = float(inp_file['input.NAMD']['max_temperature'])

        # test if min temp is less than max_temp 
        self.assertTrue( min_temp < max_temp )



def main():
    unittest.main()

if __name__ == '__main__':
    main()


