# Python 3.6 Tutorial for Beginners
# Dictionaries
# Working with keyvalue Pairs

# let's represent a student using a dictionary
student = {'name': 'John', 'age': 25, 'courses': ['Math', 'CompSci']}

#---------------------------------------------------------------------------------------------#
# dictionary operations                                                                       #
#---------------------------------------------------------------------------------------------#
# print value of one key in our dictionary
print('value of age in dictionary is:', student['age'])

# get() method is best suited for a btter response when accesing a key that doesn't exit
print('value of phone in dictionary is:', student.get('phone'))

# specify a defaut value for key that don't exist
print('value of phone in dictionary is:', student.get('phone', 'Not Found'))

# add and update entries to the dictionary using update method
student.update({'age': '27', 'phone': '555-524-5555', 'name': 'Marc'})
print('after adding and update, entries in dictionary are:', student)

# delete an entry in the dictionary
del student['courses']
print('entries in dictionary are:', student)
# or
age_deleted = student.pop('age')
print(age_deleted, 'was removed from dictionary')
print('after deleting, entries in dictionary are:', student)

# check the lenght
print('The lenght of the dictionary is:', len(student))

# print all keys in the dictionary
print('Keys in the dictonary are:', student.keys())

# print all values in the dictionary
print('Values in the dictonary are:', student.values())

# print keys and values
print('Keys and Values in the dictonary are:', student.items())
# let's loop through the dictionary using items()
for key, value in student.items():
    print(key, value)
    
#---------------------------------------------------------------------------------------------#
