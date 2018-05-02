# Python 3.6 Tutorial for Beginners
# Loops and Iterations
# For / while Loops

nums = [1, 2, 3, 4]
letters = ['a','b']
#---------------------------------------------------------------------------------------------#
# looping operations                                                                          #
#---------------------------------------------------------------------------------------------#
# let's simple print item in the nums list with for loop
for num in nums:
    print(num)

# break statement (stop looping if condition is true)
for num in nums:
    if num == 7:
        print('found')
        break
    print(num)

# continue statement (ingore a value and continue looping)
for num in nums:
    if num == 7:
        print('found')
        continue
    print(num)

# loop within a loop
for num in nums:
    for letter in letters:
        print(num, letter)

# let's say we want to run through the loop 5 times only 
# with a starting value at 1
for i in range(1, 6):
    print(i)

# while loop
x = 0

while x < 5:
    if x == 3: # break out of the loop when x is equal to 3
        break
    print(x)
    x += 1 # increment x so that its value will much the condition

#---------------------------------------------------------------------------------------------#
