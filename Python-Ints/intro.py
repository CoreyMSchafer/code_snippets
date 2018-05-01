
# Python 3.6 Tutorial for Beginners
# Working with Numeric Data
# Integers and Floats 

#let's set some integer numbers
num = 4
num1 = 5
num2 = 3
num3 = 3.68
num4 = -6
# number that get set value of number within a string
num5 = '86'
num6 = '28'

#---------------------------------------------------------------------------------------------#
# basic arithmetic operation                                                                  #
#---------------------------------------------------------------------------------------------#
# addition
add = num1 + num2
print(f'{num1} + {num2} =', add)

# subtraction
sub = num1 - num2
print(f'{num1} - {num2} =', sub)

# multiplication
multi = num1 * num2
print(f'{num1} * {num2} =', multi)

# division in python 3 give us a decimal(float) 
# eventhough we divided two intergers 
div = num1 / num2
print(f'{num1} / {num2}=', div)

# floor division drops the dicimal and only return an integer
floor_div = num1 // num2
print(f'{num1} // {num2} =', floor_div)

# exponent
expo = num1 ** num2
print(f'{num1} ** {num2} =', expo)

# modulus
modu = num1 % num2
print(f'{num1} % {num2} =', modu)
