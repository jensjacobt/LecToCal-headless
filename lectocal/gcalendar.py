# Copyright 2016 Philip Hansen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import backoff
import datetime
import dateutil.parser
import os.path
import pkg_resources
import pytz

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from . import lesson

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]


SERVICE_NAME = "calendar"
SERVICE_VERSION = "v3"

service_object = None  # only use in _get_calendar_service()

DEFAULT_TIME_ZONE = pytz.timezone("Europe/Copenhagen")
LESSON_STATUS = {"7": "normal", "2": "changed", "11": "cancelled"}


class CalendarNotFoundError(object):
    """To get the id of a calendar, the calendar must exist."""


def _new_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                _get_client_secret_path(), SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build(SERVICE_NAME, SERVICE_VERSION, credentials=creds)


def _get_client_secret_path():
    return pkg_resources.resource_filename(__name__, "credentials.json")


def _get_calendar_service():
    global service_object
    if service_object is None:
        service_object = _new_calendar_service()
    return service_object


def has_calendar(calendar_name):
    service = _get_calendar_service()
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_entry in calendar_list["items"]:
            if calendar_entry["summary"] == calendar_name:
                return True
        page_token = calendar_list.get("nextPageToken")
        if not page_token:
            return False


def create_calendar(calendar_name):
    calendar = {"summary": calendar_name, "timeZone": DEFAULT_TIME_ZONE.zone}

    service = _get_calendar_service()
    service.calendars().insert(body=calendar).execute()


def _get_calendar_id_for_name(service, calendar_name):
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_entry in calendar_list["items"]:
            if calendar_entry["summary"] == calendar_name:
                return calendar_entry["id"]
        page_token = calendar_list.get("nextPageToken")
        if not page_token:
            raise CalendarNotFoundError("Calendar: {} not found".format(calendar_name))


def _get_first_time_of_week():
    today = datetime.date.today()
    days_since_first_weekday = datetime.timedelta(days=today.weekday())
    first_day_this_week = today - days_since_first_weekday
    return datetime.datetime.combine(first_day_this_week, datetime.time.min)


def _get_last_time_in_n_weeks(n):
    today_n_weeks = datetime.date.today() + datetime.timedelta(weeks=n)
    days_to_week_end = datetime.timedelta(days=(6 - today_n_weeks.weekday()))
    last_day_n_weeks = today_n_weeks + days_to_week_end
    return datetime.datetime.combine(last_day_n_weeks, datetime.time.max)


def _get_events_in_date_range(service, calendar_id, start, end):
    all_events = []
    page_token = None
    while True:
        events = (
            service.events()
            .list(
                calendarId=calendar_id,
                pageToken=page_token,
                timeMax=DEFAULT_TIME_ZONE.localize(end).isoformat(),
                timeMin=DEFAULT_TIME_ZONE.localize(start).isoformat(),
            )
            .execute()
        )
        all_events += events["items"]
        page_token = events.get("nextPageToken")
        if not page_token:
            break
    return all_events


def _get_status_from_color(colorId):
    try:
        return LESSON_STATUS[colorId]
    except KeyError:
        return "invalid status"  # to get the event removed


def _get_datetime_from_field(field):
    return dateutil.parser.parse(field, ignoretz=True)


def _get_date_from_field(field):
    return dateutil.parser.parse(field, ignoretz=True).date()


def _parse_event_to_lesson(event):
    id = event["id"]
    summary = event["summary"]
    status = _get_status_from_color(event["colorId"])
    if "dateTime" in event["start"]:
        start = _get_datetime_from_field(event["start"]["dateTime"])
    else:
        start = _get_date_from_field(event["start"]["date"])
    if "dateTime" in event["end"]:
        end = _get_datetime_from_field(event["end"]["dateTime"])
    else:
        end = _get_date_from_field(event["end"]["date"])
    location = event.get("location", None)
    description = event.get("description", None)
    if "source" in event and "url" in event["source"]:
        link = event["source"]["url"]
    else:
        link = None
    return lesson.Lesson(id, summary, status, start, end, location, description, link)


def _parse_events_to_schedule(events):
    schedule = []
    for event in events:
        schedule.append(_parse_event_to_lesson(event))
    return schedule


def get_schedule(calendar_name, n_weeks):
    service = _get_calendar_service()
    calendar_id = _get_calendar_id_for_name(service, calendar_name)
    start = _get_first_time_of_week()
    end = _get_last_time_in_n_weeks(n_weeks)
    events = _get_events_in_date_range(service, calendar_id, start, end)
    return _parse_events_to_schedule(events)


@backoff.on_exception(backoff.expo, HttpError, max_tries=4)
def _delete_lesson(service, calendar_id, lesson_id):
    service.events().delete(calendarId=calendar_id, eventId=lesson_id).execute()


@backoff.on_exception(backoff.expo, HttpError, max_tries=4)
def _add_lesson(service, calendar_id, lesson):
    try:
        service.events().insert(
            calendarId=calendar_id, body=lesson.to_gcalendar_format()
        ).execute()
    except HttpError as err:
        # Status code 409 is conflict. In this case, it means the id already exists.
        if err.resp.status == 409:
            _update_lesson(service, calendar_id, lesson)
        else:
            raise err


@backoff.on_exception(backoff.expo, HttpError, max_tries=4)
def _update_lesson(service, calendar_id, lesson):
    service.events().update(
        calendarId=calendar_id, eventId=lesson.id, body=lesson.to_gcalendar_format()
    ).execute()


def _print_action(action, lesson):
    print(f"{action.upper()}:\n{lesson}\n\n")


def _delete_removed_lessons(service, calendar_id, old_schedule, new_schedule):
    for old_lesson in old_schedule:
        if not any(new_lesson.id == old_lesson.id for new_lesson in new_schedule):
            _delete_lesson(service, calendar_id, old_lesson.id)
            _print_action("removed", old_lesson)


def _add_new_lessons(service, calendar_id, old_schedule, new_schedule):
    for new_lesson in new_schedule:
        if not any(old_lesson.id == new_lesson.id for old_lesson in old_schedule):
            _add_lesson(service, calendar_id, new_lesson)
            _print_action("added", new_lesson)


def _update_current_lessons(service, calendar_id, old_schedule, new_schedule):
    for new_lesson in new_schedule:
        for old_lesson in old_schedule:
            if new_lesson.id == old_lesson.id:
                if new_lesson != old_lesson:
                    _update_lesson(service, calendar_id, new_lesson)
                    _print_action("updated", new_lesson)


def update_calendar_with_schedule(calendar_name, old_schedule, new_schedule):
    service = _get_calendar_service()
    calendar_id = _get_calendar_id_for_name(service, calendar_name)
    _update_current_lessons(service, calendar_id, old_schedule, new_schedule)
    _add_new_lessons(service, calendar_id, old_schedule, new_schedule)
    _delete_removed_lessons(service, calendar_id, old_schedule, new_schedule)
