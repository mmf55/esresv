from caldavHandler import DAVHandler

__author__ = 'mfernandes'

dh = DAVHandler("http://127.0.0.1:5190/test-caldav/meals.ics/", "admin-caldav", "aHsW8Jiy3P77lZIqpYqKfAsZCmNC8Yeh")

# dh = DAVHandler("http://127.0.0.1:5190/testcaldav/meals.ics/", None, None)
# add_event(self, uid, event_name, start_timestamp):
dh.add_event(123247, "Test5", 1447716529)
