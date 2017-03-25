import itertools

my_list = [1,2,3]

# combinations = itertools.combinations(my_list, 2)
# for c in combinations:
#     print c

permutations = itertools.permutations(my_list, 2)
for p in permutations:
    print p