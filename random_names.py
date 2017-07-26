''' Super simple module to get basic random names and emails'''
import random

random_first = ['John', 'Jane', 'Corey', 'Travis', 'Dave', 'Kurt', 'Neil', 'Sam', 'Mary', 'Maggie', 'Nicole', 'Steve', 'Tom']
random_last = ['Smith', 'Doe', 'Jenkins', 'Robinson', 'Davis', 'Stuart', 'Jefferson', 'Jacobs', 'Wright', 'Patterson', 'Wilks', 'Arnold']

for num in range(20):
    first = random.choice(random_first)
    last = random.choice(random_last)
    email = first.lower() + last.lower() + '@bogusemail.com'
    print(f'{first} {last} - {email}')
