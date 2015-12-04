from caldavHandler import DAVHandler

__author__ = 'mfernandes'

dh = DAVHandler("http://127.0.0.1:5190/", "admin-caldav", "FZiFFEE1Cc6FXtC8M4bjekrtbqLXyjeM")

# dh = DAVHandler("http://127.0.0.1:5190/testcaldav/meals.ics/", None, None)
# add_event(self, uid, event_name, start_timestamp):
dh.add_event('test-caldav', 123247, "Test5", 1447716529, 2)
