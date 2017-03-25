def outer():
    x = 10
    def inner():
        y = 20
    inner()
    return x + y

my_func = outer

print my_func()

# h1_tag = html_tag('h1')
# print h1_tag

# def html_tag(tag):
#     def print_tag(text):
#         return '<{0}>{1}</{0}>'.format(tag,text)
#     return print_tag

# h1_tag = html_tag('h1')
# print h1_tag('This is a headline!')
