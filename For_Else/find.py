
def find_index(to_search, target):
  for i, value in enumerate(to_search):
    if value == target:
      break
  else:
    return -1
  return i


my_list = ['Corey', 'Rick', 'John']
index_location = find_index(my_list, 'John')
print(f'Location of target is index: {index_location}')