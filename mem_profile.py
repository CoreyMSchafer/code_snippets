import psutil
import os
import sys
import time


def memory_usage_psutil():
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / float(2 ** 20)
    return '{:.2f} MB'.format(mem)
