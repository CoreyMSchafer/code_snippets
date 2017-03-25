import datetime
import pytz

a = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)

b = str(a)

print 'str(a): {}'.format(str(a))
print 'str(b): {}'.format(str(b))

print

print 'repr(a): {}'.format(repr(a))
print 'repr(b): {}'.format(repr(b))

print