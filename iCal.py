from icalendar import Calendar, Event
from datetime import timedelta

class iCal:
    def __init__(self):
        self.cal = Calendar()
        self.cal.add('prodid', '-//luyufaa//BangumiCalendar//')
        self.cal.add('version', '2.0')
        # Explicitly tell Apple Calendar the default timezone for this file
        self.cal.add('x-wr-timezone', 'Asia/Shanghai')

    def setEvent(self, summary, time, uuid, description):
        event = Event()
        event.add('summary', summary)
        
        # When 'time' is a pytz-localized object, icalendar writes:
        # DTSTART;TZID=Asia/Shanghai:20260108T220000
        event.add('dtstart', time)
        event.add('dtend', time + timedelta(minutes=30))
        
        event.add('uid', uuid)
        event.add('description', description)
        self.cal.add_component(event)

    def write(self, filename="target.ics"):
        with open(filename, 'wb') as f:
            f.write(self.cal.to_ical())