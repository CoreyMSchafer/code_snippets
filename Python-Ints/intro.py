
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

#---------------------------------------------------------------------------------------------#
# now let's see some method                                                                   #
#---------------------------------------------------------------------------------------------#
# 'type' shows the datatype
print(type(num))
print(type(num3))

# the order of operation 
print(f'{num} * {num1} + {num2} =', num * num1 + num2)
print(f'{num} * ({num1} + {num2}) =', num * (num1 + num2))

# incremention, let's increment num by 1
num += 1
num1 *= 3
print(f'num += 1 is:', num)
print(f'num1 += 3 is:', num1)

# absolute value
print('num4 is:', num4)
print('Absolute value of num4 is: ', abs(num4))

# rouding
print('num3 is:', num3)
print('round of num3 is:', round(num3))
# set how many digit we want to round to
print(f'{num1} / {num2}=', div)
print(f'{num1} / {num2} round to 2 =', round(div, 2))

#---------------------------------------------------------------------------------------------#
# comparaison operation: comparaison operators return boolean 'true' or 'false'               #
#---------------------------------------------------------------------------------------------#
# equal, a single '=' is assigment like when we set the value of num = 4
# double equal is for comparaison
print(f'is {num1} equal to {num2}?', num1 == num2)

# not equal
print(f'is {num1} not equal to {num2}?', num1 != num2)

# greater than
print(f'is {num1} greater than {num2}?', num1 > num2)

# less than
print(f'is {num1} less than {num2}?', num1 < num2)

# greater or equal to
print(f'is {num1} greater or equal to {num2}?', num1 >= num2)

# less or equal to
print(f'is {num1} less or equal to {num2}?', num1 <= num2)
#---------------------------------------------------------------------------------------------#
# casting from srting to integer                                                              #
#---------------------------------------------------------------------------------------------#
print(f'num5 value is: {num5} and num6 value is: {num2}', 'num5 + num6 = ', num5 + num6)

# let's cast them
num_5 = int(num5)
num_6 = int(num6)
print(f'num5 value is: {num_5} and num6 value is: {num_6}', 'num5 + num6 = ', num_5 + num_6)
