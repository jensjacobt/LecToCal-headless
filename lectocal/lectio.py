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

import datetime
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from lxml import html
from . import lesson


USER_TYPE = {"student": "elev", "teacher": "laerer"}
LESSON_STATUS = {None: "normal", "Ændret!": "changed", "Aflyst!": "cancelled"}
URL_TEMPLATE = "https://www.lectio.dk/lectio/{0}/SkemaNy.aspx?{1}id={2}&week={3}"
LOGIN_URL_TEMPLATE = "https://www.lectio.dk/lectio/{0}/login.aspx"
SPACER = " " + u"\u2022" + " "
cookies = None


class UserDoesNotExistError(Exception):
    """ Attempted to get a non-existing user from Lectio. """

class CookiesNotSet(Exception):
    """ Cookies not set. Login before you retrieve calendar pages. """

class IdNotFoundInLinkError(Exception):
    """ All lessons with a link should include an ID. """

class InvalidStatusError(Exception):
    """ Lesson status can only take the values Ændret!, Aflyst! and None. """

class InvalidTimeLineError(Exception):
    """ The line doesn't include any valid formatting of time. """

class InvalidLocationError(Exception):
    """ The line doesn't include any location. """

class InvalidRessourcesError(Exception):
    """ The line doesn't include any ressources. """

class InvalidGroupsError(Exception):
    """ The line doesn't include any groups. """



def _get_user_page(driver, school_id, user_type, user_id, week):
    url = URL_TEMPLATE.format(school_id, USER_TYPE[user_type], user_id, week)
    driver.get(url)
    return driver.page_source


def _get_lectio_weekformat_with_offset(offset):
    today = datetime.date.today()
    future_date = today + datetime.timedelta(weeks=offset)
    week_number = "{0:02d}".format(future_date.isocalendar()[1])
    year_number = str(future_date.isocalendar()[0])
    lectio_week = week_number + year_number
    return lectio_week


def _get_id_from_link(link):
    match = re.search(
        r"(?:absid|ProeveholdId|outboundCensorID|aftaleid)=(\d+)", link)
    if match is None:
        return None
    return match.group(1)


def _get_complete_link(link):
    return "https://www.lectio.dk" + link.split("&prevurl=", 1)[0]


def _is_status_line(line):
    match = re.search(r"Ændret!|Aflyst!", line)
    return match is not None


def _get_status_from_line(line):
    try:
        return LESSON_STATUS[line]
    except KeyError:
        raise InvalidStatusError("Line: '{}' has no valid status".format(line))


def _is_location_line(line):
    match = re.search(r"Lokaler?: ", line)
    return match is not None


def _get_location_from_line(line):
    match = re.search(r"Lokaler?: (.*)", line)
    if match is None:
        raise InvalidLocationError("No location found in line: '{}'"
                                   .format(line))
    return match.group(1)


def _is_groups_line(line):
    return line.startswith("Hold: ")


def _get_groups_from_line(line):
    match = re.search(r"Hold: (.*)", line)
    if match is None:
        raise InvalidGroupsError("No groups found in line: '{}'"
                                 .format(line))
    return match.group(1)


def _is_ressources_line(line):
    return line.startswith("Ressourcer: ")


def _get_ressources_from_line(line):
    match = re.search(r"Ressourcer: (.*)", line)
    if match is None:
        raise InvalidRessourcesError("No ressources found in line: '{}'"
                                     .format(line))
    return match.group(1)


def _is_time_line(line):
    # Search for one of the following formats:
    # 14/3-2016 Hele dagen
    # 14/3-2016 15:20 til 16:50
    # 8/4-2016 17:30 til 9/4-2016 01:00
    # 7/12-2015 10:00 til 11:30
    # 17/12-2015 10:00 til 11:30
    match = re.search(r"\d{1,2}/\d{1,2}-\d{4} (?:Hele dagen|\d{2}:\d{2} til "
                      r"(?:\d{1,2}/\d{1,2}-\d{4} )?\d{2}:\d{2})", line)
    return match is not None


def _get_date_from_match(match):
    if match:
        return datetime.datetime.strptime(match, "%d/%m-%Y").date()
    else:
        return None


def _get_time_from_match(match):
    if match:
        return datetime.datetime.strptime(match, "%H:%M").time()
    else:
        return None


def _get_time_from_line(line):
    # Extract the following information in capture groups:
    # 1 - start date
    # 2 - start time
    # 3 - end date
    # 4 - end time
    match = re.search(r"(\d{1,2}/\d{1,2}-\d{4})(?: (\d{2}:\d{2}) til "
                      r"(\d{1,2}/\d{1,2}-\d{4})? ?(\d{2}:\d{2}))?", line)
    if match is None:
        raise InvalidTimeLineError("No time found in line: '{}'".format(line))

    start_date = _get_date_from_match(match.group(1))
    start_time = _get_time_from_match(match.group(2))

    is_top = False
    if start_time:
        start = datetime.datetime.combine(start_date, start_time)
    else:
        start = start_date
        is_top = True

    end_date = _get_date_from_match(match.group(3))
    end_time = _get_time_from_match(match.group(4))

    if not end_date:
        end_date = start_date

    if end_time:
        end = datetime.datetime.combine(end_date, end_time)
    else:
        end = end_date

    return start, end, is_top


def _add_line_to_text(line, text):
    if text != "":
        text += "\n"
    text += line
    return text


def _append_section_to_summary(section, summary):
    spacer = SPACER if summary else ""
    summary += spacer + section
    return summary


def _prepend_section_to_summary(section, summary):
    spacer = SPACER if summary else ""
    summary = section + spacer + summary
    return summary


def _extract_lesson_info(tooltip):
    summary = description = event_title = groups = ressources = ""
    status = start_time = end_time = location = None
    lines = tooltip.splitlines()
    header_section = True
    is_top = False
    offset = 0

    # Find status and event title (if present) and offset
    if len(lines) >= 2:
        line = lines[0]
        if _is_status_line(line):
            status = _get_status_from_line(line)
            line = lines[1]
            offset += 1
        if not _is_time_line(line):
            event_title = line
            offset += 1

    # Get info from all lines
    for line in lines[offset:]:
        if header_section:
            if line == '' and start_time is not None:
                header_section = False
                continue
            elif _is_time_line(line):
                start_time, end_time, is_top = _get_time_from_line(line)
            elif _is_location_line(line):
                location = _get_location_from_line(line)
            elif _is_groups_line(line):
                groups = _get_groups_from_line(line)
            elif _is_ressources_line(line):
                ressources = _get_ressources_from_line(line)
            else:
                pass
                # summary = _append_section_to_summary(line, summary) # teachers (and students) added directly to event
        else:
            description = _add_line_to_text(line, description)

    # Remove extra text in the summary
    summary = summary.replace("Lærere: ", "")
    summary = re.sub(r"Lærer: [^(]*\(([^)]*)\)", r"\1", summary)

    # Construct summary and description
    if ressources:
        description = "Ressoucer: " + ressources + "\n\n" + description
    if location:
        summary = _append_section_to_summary(location, summary)
    if groups:
        summary = _prepend_section_to_summary(groups, summary)
        if groups.find("Alle") == -1:
            description = event_title + "\n\n" + description
        else:
            summary = _prepend_section_to_summary(event_title, summary)
    else:
        summary = _prepend_section_to_summary(event_title, summary)

    description = "" ################################################################################################# TODO: Handle this better
    if description == "":  # needed for comparison
        description = None

    return summary, status, start_time, end_time, location, description, is_top


def _parse_element_to_lesson(element, show_top, show_cancelled):
    link = element.get("href")
    id = None
    if link:
        id = _get_id_from_link(link)
        link = _get_complete_link(link)
    tooltip = element.get("data-tooltip")
    summary, status, start_time, end_time, location, description, is_top = \
        _extract_lesson_info(tooltip)

    if not show_top and is_top:
        return None
    elif not show_cancelled and status == "cancelled":
        return None
    # elif not location:
    #     return None ################################################################################################# TODO: Do this better
    elif (end_time - start_time).days > 5:
        return None ################################################################################################# TODO: Do this better
    else:
        location = None ################################################################################################# TODO: Undo this
        return lesson.Lesson(id, summary, status, start_time, end_time, location, description, link)


def _parse_page_to_lessons(page_source, show_top, show_cancelled):
    tree = html.fromstring(page_source)
    # Find all a elements with class s2skemabrik in page
    lesson_elements = tree.xpath("//a[contains(concat("
                                 "' ', normalize-space(@class), ' '),"
                                 "' s2skemabrik ')]")
    lessons = []
    for element in lesson_elements:
        lesson = _parse_element_to_lesson(element, show_top, show_cancelled)
        if lesson is not None:
            lessons.append(lesson)
    return lessons


def _retreive_week_schedule(driver, school_id, user_type, user_id, week, show_top, show_cancelled):
    page_source = _get_user_page(driver, school_id, user_type, user_id, week=week)
    schedule = _parse_page_to_lessons(page_source, show_top, show_cancelled)
    return schedule


def _filter_for_duplicates(schedule):
    filtered_schedule = []
    for lesson in schedule:
        if lesson not in filtered_schedule:
            filtered_schedule.append(lesson)
    return filtered_schedule


def _last_updated_event():
    id = "updated"
    summary = "Opdateret " + datetime.datetime.now().strftime("%d/%m %H:%M")
    status = None

    now = datetime.datetime.now()
    monday = (now - datetime.timedelta(days = now.weekday())).date()
    start_time = end_time = monday

    description = None
    location = None
    link = None
    l = lesson.Lesson(id, summary, status, start_time, end_time, location, description, link)
    return l


def _not_on_a_schedule_page(driver):
    return len(driver.find_elements(By.CLASS_NAME, "tidsreg-wrapper")) == 0


def _retreive_user_schedule(driver, school_id, user_type, user_id, n_weeks, show_top, show_cancelled):
    schedule = []
    for week_offset in range(n_weeks + 1):
        week = _get_lectio_weekformat_with_offset(week_offset)
        week_schedule = _retreive_week_schedule(
            driver, school_id, user_type, user_id, week, show_top, show_cancelled)
        if week_offset == 0 and _not_on_a_schedule_page(driver):
            raise UserDoesNotExistError(
                f"Couldn't log in user - school: {school_id}, type: {user_type}, id: {user_id} - in Lectio.")
        schedule += week_schedule
    filtered_schedule = _filter_for_duplicates(schedule)
    filtered_schedule.append(_last_updated_event())
    return filtered_schedule


def _get_driver():
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        service = webdriver.ChromeService(executable_path = '/usr/lib/chromium-browser/chromedriver')
        driver = webdriver.Chrome(options = options, service = service)
    except:
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            driver = webdriver.Chrome(options=options)
        except:
            try:
                options = webdriver.FirefoxOptions()
                options.add_argument("-headless")
                driver = webdriver.Firefox(options=options)
            except:
                    raise Exception("Unable to open browser (tried Chrome and Firefox)")
    return driver


def _login(driver, school_id, username, password):
    driver.get(LOGIN_URL_TEMPLATE.format(school_id))

    usernameInput = driver.find_element(By.NAME, "m$Content$username")
    usernameInput.send_keys(username)
    passwordInput = driver.find_element(By.NAME, "m$Content$password")
    passwordInput.send_keys(password + Keys.RETURN)
    

def get_schedule(school_id, user_type, user_id, n_weeks, show_top, show_cancelled, username, password):
    try:
        driver = _get_driver()

        print("Using", driver.capabilities.get("browserName", "No name browser"))

        _login(driver, school_id, username, password)

        return _retreive_user_schedule(driver, school_id, user_type, user_id, n_weeks, show_top, show_cancelled)
    finally:
        if not driver is None:
            driver.quit()


def main():
    file = open("example.html", "r", encoding="utf-8") # a schedule page from Lectio - get your own
    page_source = file.read()
    file.close()
    
    # info = _parse_page_to_lessons(content, False, False)
    # from pprint import pprint
    # for i in info:
    #     pprint(i)
    #     print()
    #     print()
    
    schedule = _parse_page_to_lessons(page_source, False, False)
    
    r = _filter_for_duplicates(schedule) + [_last_updated_event()]

    # for i in r:
    #     print(i)
    #     print()
    #     print()

    return r


if __name__ == '__main__':
    main()
