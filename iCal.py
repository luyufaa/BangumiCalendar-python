from icalendar import Calendar, Event
from datetime import timedelta

class iCal:
    def __init__(self):
        self.cal = Calendar()
        self.cal.add('prodid', '-//BangumiCalendar//')
        self.cal.add('version', '2.0')
        self.cal.add('x-wr-timezone', 'Asia/Shanghai')

    def setEvent(self, summary, time, uuid, descripion):
        event = Event()
        event.add('summary', summary)
        event.add('dtstart', time)
        event.add('dtend', time + timedelta(minutes=30))
        event.add('uid', uuid)
        event.add('description', descripion)
        self.cal.add_component(event)

    def write(self, filename="target.ics"):
        with open(filename, 'wb') as f:
            f.write(self.cal.to_ical())