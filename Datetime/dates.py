import datetime
import pytz

# Naive
# d = datetime.date(2001, 9, 11)

tday = datetime.date.today()


# weekday() - Monday is 0 and Sunday is 6
# print(tday)

# isoweekday() - Monday is 1 and Sunday is 7
# print(tday)


# datetime.timedelta(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0)

tdelta = datetime.timedelta(hours=12)

# print(tday + tdelta)

# date2 = date1 + timedelta
# timedelta = date1 + date2

bday = datetime.date(2016, 9, 24)

till_bday = bday - tday

# print(till_bday.days)

t = datetime.time(9, 30, 45, 100000)

# dt = datetime.datetime.today()
# dtnow = datetime.datetime.now()
# print(dir(datetime.datetime))
# print(dt)
# print(dtnow)

dt = datetime.datetime(2016, 7, 24, 12, 30, 45, tzinfo=pytz.UTC)
# print(dir(dt))

dt_utcnow = datetime.datetime.now(tz=pytz.UTC)
# print(dt_utcnow)

dt_utcnow2 = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
# print(dt_utcnow2)

# dt_mtn = dt_utcnow.astimezone(pytz.timezone('US/Mountain'))
# print(dt_mtn)

dt_mtn = datetime.datetime.now()

mtn_tz = pytz.timezone('US/Mountain')
dt_mtn = mtn_tz.localize(dt_mtn)

# print(dt_mtn)

dt_east = dt_mtn.astimezone(pytz.timezone('US/Eastern'))
# print(dt_east)

print(dt_mtn.strftime('%B %d, %Y'))

dt_str = 'July 24, 2016'
dt = datetime.datetime.strptime(dt_str, '%B %d, %Y')
print(dt)

# strftime - Datetime to String
# strptime - String to Datetime
