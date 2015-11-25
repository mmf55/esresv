from datetime import datetime
from icalendar import Calendar, Event, vDatetime
from caldav.objects import Principal
import caldav
import sqlite3
import hashlib

__author__ = 'mfernandes'

DATABASE = '/var/www/escaldav/Specific/db/db.sqlite'


class DAVHandler:
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password
        self.client = caldav.DAVClient(self.url, None, self.username, self.password, None, False)

    def add_calendar(self):
        principal = self.client.principal()
        principal.calendar_home_set = self.url + "meals.ics/"
        cal_id = "default"
        principal.make_calendar(name="meals.ics", cal_id=cal_id).save()

    def add_event(self, uid, event_name, start_timestamp):
        # client = caldav.DAVClient(self.url)
        principal = self.client.principal()
        cal = Calendar()
        cal['version'] = "2.0"
        cal['prodid'] = "//Radicale//NONSGML Radicale Server//EN"

        event = Event()
        event['uid'] = uid
        event['dtstart'] = vDatetime(datetime.fromtimestamp(start_timestamp)).to_ical()
        event['summary'] = event_name
        event['x-radicale-name'] = str(uid) + '.ics'

        cal.add_component(event)

        #         vcal = """BEGIN:VCALENDAR
        # VERSION:2.0
        # PRODID:-//Example Corp.//CalDAV Client//EN
        # BEGIN:VEVENT
        # UID:0123456
        # DTSTAMP:20151101T182145Z
        # DTSTART:20151101T170000Z
        # DTEND:20151101T180000Z
        # SUMMARY:This is an event.
        # END:VEVENT
        # END:VCALENDAR
        # """
        print cal.to_ical
        headers = {'Content-Type': 'text/calendar',
                   'charset': 'utf-8',
                   'if-none-match': '*'}

        #	headers = {'Content-Type': 'text/calendar', 'charset': 'utf-8'}
        self.client.put(self.url + str(uid) + '.ics', cal.to_ical(), headers)
        #        calendars = principal.calendars()
        #        if len(calendars) == 0:
        #            print len(calendars)
        #            self.add_calendar()
        #	    principal = self.client.principal()
        #	    calendars = principal.calendars()
        #	print len(calendars)
        #        calendar = calendars[0]
        #        calendar.add_event(cal.to_ical())
        return 'OK'
