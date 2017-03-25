from collections import namedtuple

# list / tuple
color = (55,155,255)

# dictionary
color = {'red': 55, 'green': 155, 'blue': 255}

# namedtuple
Color = namedtuple('Color', ['red', 'green', 'blue'])
color = Color(blue=55,green=155,red=255)

