# Python 3.6 Tutorial for Beginners
# import modules and exploring the standard library
#---------------------------------------------------------------------------------------------#
# import my module
import my_module
# 'mm' will refer to my_module
import my_module as mm
# import functions and variables from my_module
from my_module import find_index as find, test 

# standards library contains module written by developer
# optimized and put to our disposal for future use
# let's import some modules from the standard library
import os # gives access to the underlines of the operting system
import math
import random
import datetime
import calendar
#---------------------------------------------------------------------------------------------#
# let's create a course list
courses = ['History', 'Math', 'Physics', 'CompSci']

# call a function from my_module
index = my_module.find_index(courses, 'Math')
print('item index on the list is:',index)

# call a function from my_module using mm
index = mm.find_index(courses, 'CompSci')
print('item index on the list is:', index)

# let's find index using find from import
index = find(courses, 'Physics')
print('item index on the list is:', index)
print('test imported from my_module is:', test)

# let's print a random item from the list
random_course = random.choice(courses)
print('print random course from course list:', random_course)

# let's do some math ops
# find radian of 90 degrees
rads = math.radians(90)
print('radian of 90 is:', rads)
# sign of radian
print('sign of radian is:', math.sin(rads))

# get today's date
today = datetime.date.today()
print("Today's date is:", today)

# let's use calender module to check leap year
print('is 2017 a leap year?:', calendar.isleap(2017))
print('is 2020 a leap year?:', calendar.isleap(2020))

# check current directory
print('the currrent directory is:', os.getcwd())

#---------------------------------------------------------------------------------------------#
