# Python 3.6 Tutorial for Beginners
# Working with Lists, Tuples, and Sets

#---------------------------------------------------------------------------------------------#
# basic list slicing operation                                                                #
#---------------------------------------------------------------------------------------------#
# let's create a list of fruits
fruits = ['bananas', 'mango', 'berry', 'apple', 'cherry', 'strawberry', 'melon']
print(fruits)

#get the number of item in the list
print('The number of items in the list is:', len(fruits))

# print an item in the list using index
print('the first item in the list is:', fruits[0])
# print the last item on the list 
# the last item can be find by pass index -1 
# this is a good way to find the last item when the lenght of the list is unknown
print('the last item on the list is:', fruits[-1])

# print a range of items in the list
print('these the first 3 items on the list:', fruits[0:3])
# or
print('these the first 3 items on the list:', fruits[:3])
# print item from index 3 to last item on the list, not including item on index 3 
print('these the first 3 items on the list:', fruits[3:])

#---------------------------------------------------------------------------------------------#
# basic list slicing operation                                                                #
#---------------------------------------------------------------------------------------------#
# add an item on the list at the end of the list
fruits.append('piche')
print('Items on list are:', fruits)

# add item to a specific location in the list
fruits.insert(4, 'durian')
print('Items on list are now:', fruits)

# add multiple items on the list
fruits_2 = ['apricot','pineapple', 'plum', 'orange', 'avocado']
# let's add fruit_2 list to fruits list
fruits.extend(fruits_2)
print('Items on fruits list are now:', fruits)

# remove item from list
fruits.remove('plum')
print('after remove, items on list are now:', fruits)

# pop remove the last item on the list by default and return the item removed
popeditem = fruits.pop()
print('item removed from the list is:', popeditem)

# Empty Lists
empty_list = []
empty_list = list()

# Empty Tuples
empty_tuple = ()
empty_tuple = tuple()

# Empty Sets
empty_set = {} # This isn't right! It's a dict
empty_set = set()
