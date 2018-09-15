# given an aary of numbers, find a pair of number that add up to 10 

# The function should return or print out the pair of number that add up to 10
# we will resolve this sulation with a run time of O(n)

def IsPairOf10 (given_array):
  # this hash table will
  seen_numbers = {}
  for item in given_array:
    if (10 - item) in seen_numbers:
      print("The following pair of number in array adds up to 10" + str(item) + " and " + str(10-item))
    else:
