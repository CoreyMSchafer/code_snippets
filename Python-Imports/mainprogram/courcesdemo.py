from .indexer import mymodule

courses = ['History', 'Math', 'Physics', 'CompSci']

def main():
    the_course = mymodule.find_index(courses, 'History')
    print (the_course)

