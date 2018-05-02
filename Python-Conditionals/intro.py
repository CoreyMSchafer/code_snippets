# Python 3.6 Tutorial for Beginners
# Conditionals and Booleans
# if, Else, and Elif Statements

#---------------------------------------------------------------------------------------------#
# conditional operation (comaparaison)                                                        #
#---------------------------------------------------------------------------------------------#
# let's create a varibale
language = 'java'

if language == 'python':
    print('langauge is python')
elif language == 'java':
    print('language is java')
else:
    print('no mouch found')

#---------------------------------------------------------------------------------------------#
# boolean operation (and, or, not)                                                            #
#---------------------------------------------------------------------------------------------#
# let's create a varibale
user = 'Admin'
logged_in = True
IsLogged_in = False

# and operator (evaluate to true if both conditions aare true)
if user == 'Admin' and logged_in:
    print('admin Page')
else:
    print('wrong credentials')

# or operator (evaluate to true is one of the conditions is true)
if user == 'Admin' or IsLogged_in:
    print('admin Page')
else:
    print('wrong credentials')

# not operator is used to switched a boolean
# changing a true to false or fale to true
# if not 'False' evaluate to 'true'
if not IsLogged_in:
    print('Please log in')
else:
    print('welcome')

#---------------------------------------------------------------------------------------------#
