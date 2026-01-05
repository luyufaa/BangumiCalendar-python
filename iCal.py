from icalendar import Calendar, Event
from datetime import timedelta

class iCal:
    def __init__(self):
        self.cal = Calendar()
        self.cal.add('prodid', '-//BangumiCalendar//')
        self.cal.add('version', '2.0')

    def setEvent(self, summary, time, uuid, description):
        event = Event()
        event.add('summary', summary)
        event.add('dtstart', time) # 'time' is already UTC-aware from util.py
        event.add('dtend', time + timedelta(minutes=30))
        event.add('uid', uuid)
        event.add('description', description)
        self.cal.add_component(event)

    def write(self, filename="target.ics"):
        with open(filename, 'wb') as f:
            # icalendar will append 'Z' to timestamps if tzinfo=timezone.utc
            f.write(self.cal.to_ical())