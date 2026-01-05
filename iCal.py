from icalendar import Calendar, Event, vDatetime
from datetime import timedelta

class iCal:
    def __init__(self):
        self.cal = Calendar()
        self.cal.add('prodid', '-//BangumiCalendar//')
        self.cal.add('version', '2.0')
        # This header helps some apps realize the file uses standard offsets
        self.cal.add('x-wr-timezone', 'UTC') 

    def setEvent(self, summary, time, uuid, description):
        event = Event()
        event.add('summary', summary)
        
        # Use vDatetime to ensure the 'Z' is explicitly handled
        event.add('dtstart', vDatetime(time))
        event.add('dtend', vDatetime(time + timedelta(minutes=30)))
        
        event.add('uid', uuid)
        event.add('description', description)
        self.cal.add_component(event)

    def write(self, filename="target.ics"):
        with open(filename, 'wb') as f:
            f.write(self.cal.to_ical())