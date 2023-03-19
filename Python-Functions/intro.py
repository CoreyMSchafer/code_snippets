# Python 3.6 Tutorial for Beginners
# functions
#---------------------------------------------------------------------------------------------#

def hello_func():
    print('hello function')
# execute function
hello_func()

def hello_func1():
    return 'hello function!'
# now that the function returns a string
# we can print it
print(hello_func1())

# passing argument to the function
# let's customize the greeting that the function reurn
def hello_func2(name):
    return 'hello {}, welcome to my function'.format(name)
# we can print it
print(hello_func2('Steve'))


def hello_func3(name='friend'):
    return 'hello {}, welcome to my function'.format(name)
# now if now argument is passed the function name will be friend by defult
print(hello_func3())
# or
print(hello_func3(name = 'Frank'))

# '*arg' are position arguments
# '**kargs' are key word arguments
def student_info(*args, **kwargs):
    print(args)
    print(kwargs)


courses = ['math', 'art']
info = {'name': 'Lee', 'age': 25}
# now let's pass these argument ot the function
student_info(*courses, **info)


# Number of days per month. First value placeholder for indexing purposes.
month_days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def is_leap(year):
    # this line is a doc string, it helps documment what a function 
    # or a class is suppoed to do
    """Return True for leap years, False for non-leap years."""

    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year, month):
    """Return number of days in that month in that year."""

    # year 2017
    # month 2
    if not 1 <= month <= 12:
        return 'Invalid Month'

    if month == 2 and is_leap(year):
        return 29

    return month_days[month]

# print days in month
print(days_in_month(2017, 5))

#---------------------------------------------------------------------------------------------#
