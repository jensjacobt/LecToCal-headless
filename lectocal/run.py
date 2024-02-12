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

import argparse
import getpass
import sys
from . import lectio
from . import lesson
from . import gcalendar


def _get_arguments():
    parser = argparse.ArgumentParser(description="Scrapes a Lectio schedule "
                                     "and syncs it to Google Calendar.")
    parser.add_argument("school_id",
                        type=int,
                        help="ID of the school user belongs to in Lectio.")
    parser.add_argument("user_type",
                        choices=["student", "teacher"],
                        help="User type in Lectio. "
                        "(options: student, teacher)")
    parser.add_argument("user_id",
                        type=int,
                        help="User's ID in Lectio.")
    parser.add_argument("--calendar",
                        default="Lectio",
                        help="Name to use for the calendar inside "
                        "Google Calendar. (default: Lectio)")
    parser.add_argument("--login",
                        default="",
                        type=str,
                        help="The username from a Lectio login.")
    parser.add_argument("--weeks",
                        type=int,
                        default=4,
                        help="Number of weeks to parse the schedule for. "
                        "(default: 4)")
    parser.add_argument('--showtop',
                        default=False,
                        dest='show_top',
                        action='store_true',
                        help="If set, sync events from the Lectio's header to Google Calendar.")
    parser.add_argument('--showcancelled',
                        default=False,
                        dest='show_cancelled',
                        action='store_true',
                        help="If set, sync cancelled events to Google Calendar.")

    return parser.parse_args()

def sync(school_id, user_type, user_id, calendar_name,
         username, password, weeks, show_top, show_cancelled):
    """
    Sync calendar from Lectio to Google
    """
    if not gcalendar.has_calendar(calendar_name):
        gcalendar.create_calendar(calendar_name)

    lectio_schedule = lectio.get_schedule(
        school_id, user_type, user_id, weeks, 
        show_top, show_cancelled, username, password)
    
    google_schedule = gcalendar.get_schedule(calendar_name, weeks)

    gcalendar.update_calendar_with_schedule(
        calendar_name, google_schedule, lectio_schedule)

def main():
    a = _get_arguments()

    try:
        if(a.login):
            login = a.login
        else:
            login = input("Lectio username: ")
        password = getpass.getpass(prompt="Lectio password: ")
    except:
        print("\nLogin cancelled")
        sys.exit()

    try:
        sync(a.school_id, a.user_type, a.user_id, a.calendar, 
             login, password, a.weeks, a.show_top, a.show_cancelled)
    except Exception as e:
        if type(e) == lectio.UserDoesNotExistError:
            message = ("Unable to log in.\n"
                       "Did you type the username and password, correctly?\n"
                       "(And did you specify school_id, user_type, and user_id, correctly?)\n"
                       "(And can you access Lectio from your web browser?)")
            print(message, file=sys.stderr)
            sys.exit(1)
        else:
            message = "An error occured. If it continues, then submit an issue with the following dump:"
            print(message, file=sys.stderr)
            raise e


if __name__ == "__main__":
    main()
