
def get_number(word):
    start=0
    number = ''
    for i in word:
        if start:
            number = number + i
        if i == '=':
            start = 1

    return float(number)

def get_some(word):

    word = word.split("=")[1]
    print word
        

    #return float(number)


current_rstr="ala10_us.RST.2"

try:
    r_file = open(current_rstr, "r")
except IOError:
    print 'Warning: unable to access template file %s' % current_rstr

tbuffer = r_file.read()
r_file.close()

print tbuffer

tbuffer = tbuffer.split()

line = 2
for word in tbuffer:
    if word == '/':
        line = 3
    if word.startswith("r2=") and line == 2:
        print word
        #print get_number(word)
        #print get_some(word)
        num_list = word.split('=')
        print num_list[1]
    if word.startswith("r3=") and line == 2:
        print word
        print get_number(word)
    

    if word.startswith("r2=") and line == 3:
        print word
        print get_number(word)
    if word.startswith("r3=") and line == 3:
        print word
        print get_number(word)
   

