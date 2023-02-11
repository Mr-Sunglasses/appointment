"""Module: caldav

Handle connection to a CalDAV server.
"""
from caldav import DAVClient
from datetime import datetime
from ..database import schemas


class CalDavConnector:
  def __init__(self, url: str, user: str, password: str):
    # store credentials of remote location
    self.url = url
    self.user = user
    self.password = password
    # connect to CalDAV server
    self.client = DAVClient(url=url, username=user, password=password)


  def list_calendars(self):
    """find all calendars on the remote server"""
    calendars = []
    principal = self.client.principal()
    for c in principal.calendars():
      # TODO: validate c.name and c.url
      calendars.append(schemas.CalendarConnection(
        title=c.name,
        url=str(c.url),
        user=self.user,
        password=self.password
      ))
    return calendars


  def list_events(self, start, end):
    """find all events in given date range on the remote server"""
    calendar = self.client.calendar(url=self.url)
    result = calendar.search(
      start=datetime.strptime(start, '%Y-%m-%d'),
      end=datetime.strptime(end, '%Y-%m-%d'),
      event=True,
      expand=True
    )
    events = []
    for e in result:
      events.append(schemas.Event(
        title=str(e.vobject_instance.vevent.summary.value),
        start=str(e.vobject_instance.vevent.dtstart.value),
        end=str(e.vobject_instance.vevent.dtend.value),
        description=e.icalendar_component['description'] if 'description' in e.icalendar_component else ''
      ))
    return events


  def create_event(self, event: schemas.Event, attendee: schemas.AttendeeBase):
    """add a new event to the connected calendar"""
    calendar = self.client.calendar(url=self.url)
    # save event
    caldavEvent = calendar.save_event(
      dtstart=datetime.fromisoformat(event.start),
      dtend=datetime.fromisoformat(event.end),
      summary=event.title,
      description=event.description
    )
    # save attendee data
    caldavEvent.add_attendee((attendee.name, attendee.email))
    caldavEvent.save()
    return event


  def delete_events(self, start):
    """delete all events in given date range from the server"""
    calendar = self.client.calendar(url=self.url)
    result = calendar.events()
    count = 0
    for e in result:
      if str(e.vobject_instance.vevent.dtstart.value).startswith(start):
        e.delete()
        count += 1
    return count
