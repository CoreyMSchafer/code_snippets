from __future__ import print_function

a = [1,2,3,4,5]
print(a)
print('Address of a is: {}'.format(id(a)))

a[0] = 6
print(a)
print('Address of a is: {}'.format(id(a)))