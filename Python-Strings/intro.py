# Python 3.6 Tutorial for Beginners
# Working with Textual Data 

# let's define a message to print
messsage = 'Hello World, Bleach is the best Anime of all time'
# print welcome message
print(messsage)

#---------------------------------------------------------------------------------------------#
# basic string manipulation                                                                   #
#---------------------------------------------------------------------------------------------#
# print the lenght of the string message
print('The lenght of the string message is: ', len(messsage))

# print a specific caractere by passing an index
print(messsage[23], messsage[38]) 

# print a range of charactere in the string
# this technic is called slicing
print(messsage[0:11])
# which is similar to 
print(messsage[:11])

# a method is a function that belongs to an object
# let's look on some of the string method
# capitalized the first char 
print(messsage.capitalize())
# all lowercase
print(messsage.lower())
# all uppercase
print(messsage.upper())
# count how many l char in the string message
print(messsage.count('l'))

# let's replace a word in the string
new_message = messsage.replace('World', 'Universe')
print(new_message)

#---------------------------------------------------------------------------------------------#
# string concatenation                                                                        #
#---------------------------------------------------------------------------------------------#
# now let's add multiple string and concatenate them together
# using placeholders and string format
gretting = 'Hello'
name = 'my friend'
my_message = "it's good to see gain!"
conversation = '{} {}, {}'.format(gretting, name, my_message)
print(conversation)
# or 
my_conversation = f'{gretting} {name.upper()}, {my_message}'
print(my_conversation)

# now the most interesting one trick when learning python
# 'dir' function shows you all the attribute and method you 
# can do with for a variable passed to it.
# print(dir(gretting))
# 'help' gives you more information, 
# including what those methods do
# print(help(str))
# print(help(str.count))
#---------------------------------------------------------------------------------------------#