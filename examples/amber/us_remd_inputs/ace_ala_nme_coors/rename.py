import os

index = 0
for filename in os.listdir("."):

    
    #print len(filename)
    if len(filename) > 20:
        n_filename = filename[0:19]
        # print n_filename   
        n_filename = n_filename + str(index) + ".0"
        index += 1
        os.rename(filename, n_filename) 
    

        """
		if filename[19] == '0':
			st = ''
			if filename[21]:
				st += filename[21]
			if len(filename) == 23:
				st += filename[22]
				n_filename = filename[:-4]
				n_filename  = n_filename + st + ".0"
				#print "file: {0}".format(filename)
				os.rename(filename, n_filename)
			else:
				n_filename = filename[:-3]
				n_filename  = n_filename + st + ".0"
				#print "file: {0}".format(filename)
				os.rename(filename, n_filename)
        """
        
             
