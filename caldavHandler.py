from datetime import datetime
from icalendar import Calendar, Event, vDatetime
from caldav.objects import Principal
import caldav
import sqlite3
import hashlib

__author__ = 'mfernandes'


class DAVHandler:
    """
        Handles the events on the CALDAV server.
    """
    def __init__(self, url, username, password):
        self.url = url
        self.username = username
        self.password = password
        self.client = caldav.DAVClient(self.url, None, self.username, self.password, None, False)

    def add_event(self, username, uid, event_name, start_timestamp, quantity):
        """
        Adds a new event with the given parameters in a given username calendar.
        :param username: username of the calendar to insert the event.
        :param uid: UID tha identifies the event in the calendar.
        :param event_name: Event name.
        :param start_timestamp: The date where the event are scheduled.
        :param quantity: The quantity reserved.
        :return: Keyword 'OK'
        """
        cal = Calendar()
        cal['version'] = "2.0"
        cal['prodid'] = "//Radicale//NONSGML Radicale Server//EN"

        event = Event()
        event['uid'] = uid
        event['dtstart'] = vDatetime(datetime.fromtimestamp(start_timestamp)).to_ical()
        event['summary'] = event_name
        event['description'] = 'Quantity: ' + str(quantity)
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
        print cal.to_ical()
        headers = {'Content-Type': 'text/calendar',
                   'charset': 'utf-8',
                   'if-none-match': '*'}

        self.client.put(self.url + username + '/calendar.ics/' + str(uid) + '.ics', cal.to_ical(), headers)
        return 'OK'

    def update_event(self, username, uid, event_name, start_timestamp, quantity):
        """
        Update the info about a specific event on the user calendar.
        :param username: username of the calendar to insert the event.
        :param uid: UID tha identifies the event in the calendar.
        :param event_name: Event name.
        :param start_timestamp: The date where the event are scheduled.
        :param quantity: The quantity reserved.
        :return: Keyword 'OK'
        """
        cal = Calendar()
        cal['version'] = "2.0"
        cal['prodid'] = "//Radicale//NONSGML Radicale Server//EN"

        event = Event()
        event['uid'] = uid
        event['dtstart'] = vDatetime(datetime.fromtimestamp(start_timestamp)).to_ical()
        event['summary'] = event_name
        event['description'] = 'Quantity: ' + str(quantity)
        event['x-radicale-name'] = str(uid) + '.ics'

        cal.add_component(event)

        headers = {'Content-Type': 'text/calendar',
                   'charset': 'utf-8'}
        self.client.put(self.url + username + '/calendar.ics/' + str(uid) + '.ics', cal.to_ical(), headers)
        return 'OK'

    def delete_event(self, username, uid):
        """
        Deletes a specific event on the user calendar.
        :param username: username of the calendar to insert the event.
        :param uid: UID tha identifies the event in the calendar.
        :return: Keyword 'OK'
        """
        self.client.delete(self.url + username + '/calendar.ics/' + str(uid) + '.ics')
        return 'OK'
