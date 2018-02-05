
from __future__ import print_function
import httplib2
import os
import logging
import string
import datetime
import urllib
import re
import json

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage
from dateutil.parser import parse

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'

# Settings
calendarName = "SpaceX Launches"
timeZone = "America/Denver"

def scrapePage():

    # Get raw html
    url = "https://www.reddit.com/r/spacex/wiki/launches/manifest"
    f = urllib.urlopen(url)
    output = f.read().splitlines()

    # Parse and clean results
    results = output[output.index("##Upcoming Falcon launches"):output.index("##Past Launches")]
    events = []

    for event in results:
        event = event.split('|')
        event = [x for x in event if not "---" in x]
        event = [x for x in event if not x == ""]

        eventStrip = []
        for x in event:
            x = x.strip()
            eventStrip.append(x)

        events.append(eventStrip)

    events = [event for event in events if len(event) != 0]
    
    # Create events
    launchEvents = []
    for event in events:

        # Get date and time
        dateTime = event[0]
        if "[" in dateTime:
            dateTime = dateTime.replace("[","")
            dateTime = dateTime.replace("]","")

        # Skip if not real date
        try:
            parsedDateTime = parse(dateTime)
            formattedDate = string.replace(str(parsedDateTime)," ","T")
        except:
            continue

        # Skip if day not given - dateutils.parser defaults to last day of the month if a day isn't given 
        if not str(parsedDateTime.day) in dateTime:
            logging.info("Skipping " + event[6] + " " + dateTime)
            continue 

        logging.info("Adding " + event[6] + " " + dateTime + ":")
        logging.info(event)

        # Make calendar object
        # calEvent = {'start': {'timeZone': 'GMT', 'dateTime': '2018-01-31T21:34:00-04:04'},'end': {'timeZone': 'GMT', 'dateTime': '2018-01-31T21:34:00-04:04'}, 'description': 'A SpaceX Falcon 9 rocket will launch EchoStar 23 communications satellite for EchoStar Corp. EchoStar 23, based on a spare platform from the canceled CMBStar 1 satellite program, will provide direct-to-home television broadcast services over Brazil. Delayed from 3rd quarter, 4th quarter, Jan. 8, Jan. 26, Jan. 30, Feb. 3 and Feb. 28. [', 'location': 'LC-39A, Kennedy Space Center, Florida', 'summary': 'Falcon 9 EchoStar 23'}
        calEvent = {
            'summary':event[1],
            'location': event[2],
            'description': event[5],
            'start':{
                'dateTime':formattedDate, 
                'timeZone':'GMT'
            },
            'end':{
                'dateTime':formattedDate,
                'timeZone':'GMT'
            },
            "reminders": {
                "useDefault": "false",
                "overrides": [
                  {
                    "method": "popup",
                    "minutes": "30"
                  }
                ]
            },
            'colorId': 3
        }

        launchEvents.append(calEvent)

    return launchEvents

def updateCalendar(service):
    
    try:
        events = scrapePage()
        
        #Delete old Launches calendar
        launchCalID = getCalendarIdByName(service, calendarName)

        if not launchCalID is None:
            logging.info("Deleting old calendar")
            service.calendars().delete(calendarId=launchCalID).execute()

        #Create new Launches calendar
        calendar = {
            'summary': calendarName,
            'timeZone': timeZone
        }
        created_calendar = service.calendars().insert(body=calendar).execute()

        #Add new events
        newLaunchCalID = getCalendarIdByName(service, calendarName)
        for event in events:
            try:
                service.events().insert(calendarId=newLaunchCalID, body=event).execute()
            except:
                logging.info("Error adding event")
                pass

        logging.info("Successfully updated calendar")

    except Exception as e:
        if hasattr(e, 'message'):
            logging.error(e.message)
        else:
            logging.error(e)

def getCalendarIdByName(service, calName):
    page_token = None
    thisID = None
    while True:
      calendar_list = service.calendarList().list(pageToken=page_token).execute()
      for calendar_list_entry in calendar_list['items']:
        if calendar_list_entry['summary'] == calName:
            thisID = calendar_list_entry['id'];
            break
        
      page_token = calendar_list.get('nextPageToken')
      if not page_token:
        break

    return thisID

def get_credentials():

    # Gets valid user credentials from storage
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, 'credentials')
    credential_path = os.path.join(credential_dir, 'google-calendar-credentials.json')
    store = Storage(credential_path)
    credentials = store.get()

    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)

    return credentials

if __name__ == '__main__':

    # Set up logging
    if not os.path.exists("logs"):
        os.makedirs("logs")
    logging.basicConfig(filename='logs/log_' + str(datetime.date.today()) + '.txt',level=logging.DEBUG)

    # Create new calendar
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)
    updateCalendar(service)