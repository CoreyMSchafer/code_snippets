import time

ef_cache = {}

def expensive_func(num):
    if num in ef_cache:
        return ef_cache[num]

    print "Computing {}...".format(num)
    time.sleep(1)
    result = num*num
    ef_cache[num] = result
    return result

result = expensive_func(4)
print result

result = expensive_func(10)
print result

result = expensive_func(4)
print result

result = expensive_func(10)
print result