import codecs
import datetime
import os
import sqlite3
import time
import urllib
import urlparse

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException

def init_browser():
    global browser
    browser = webdriver.Chrome()

def main():
    # open the page
    init_browser()
    nav_to_url(page_url_stub + pac_pool_id)

    nav_to_date(2018, 6, 15)
    print get_date()

    browser.quit()


# options
# timeout interval (seconds)
default_timeout = 59.

page_url_stub = 'https://nike.uwaterloo.ca/FacilityScheduling/FacilitySchedule.aspx?FacilityId='
pac_pool_id = '5d72208a-069d-4931-aaa6-9527346efc6f'

# other initialization
month_num2str = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
    7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'
}
month_str2num = {name: number for (number, name) in month_num2str.items()}


def get_date():
    """
    Scrapes the date of the schedule currently being viewed.

    Returns
    -------
    year : int
    month : int
    day : int
    """

    elem_days = browser.find_elements_by_class_name('dxscDateHeader_Metropolis')

    assert len(elem_days) == 1, "%d dates found on page. Expecting page showing one day's schedule." % len(elem_days)
    elem_day = elem_days[0]

    day_str, month_str, year_str = elem_day.get_attribute('title').split()

    return int(year_str), month_str2num[month_str], int(day_str)


def wait_for_page_load(timeout_sec, fun, *args, **kwargs):
    """
    Executes a function triggering dynamically loaded content, and returns when it finishes loading.

    In other words, makes an asynchronous function synchronous.

    Parameters
    ----------
    timeout_sec : float
        Length of time to wait for page to load before raising a RuntimeError.
    fun : function
        Function to call.
    *args, **kwargs : iterable
        Arguments to pass to fun.
    """

    # watch date element -- it should expire when page load finishes, resulting in an exception
    elem_day = browser.find_element_by_class_name('dxscDateHeader_Metropolis')

    fun(*args, **kwargs)

    time_slept = 0.

    try:
        while time_slept < timeout_sec:
            elem_day.get_attribute('title')  # check property to trigger exception
            time.sleep(0.5)
            time_slept += 0.5

        # if the loop exits normally, too much time has passed
        raise RuntimeError('Timeout occurred when waiting for page to load.')
    except StaleElementReferenceException:
        pass

    return


def nav_to_date(year, month, day, timeout=default_timeout):
    """
    Navigate the page to the schedule for a particular date.

    Date must fall within a range between today and two years from today.

    Parameters
    ----------
    year : int
    month : int
    day : int
    timeout : float
        Timeout, in seconds, to wait for the page to load.
    """

    today = datetime.date.today()
    two_years_from_today = today + datetime.timedelta(2*365)  # add days to avoid leap year problems
    requested_date = datetime.date(year, month, day)

    if requested_date < today or requested_date > two_years_from_today:
        raise ValueError('Date must fall between today and two years from today.')

    js_source = '''
    // first, create a fake calendar object
    var cal = {};
    cal.GetValue = function() {return new Date(%d, %d, %d, %d);};

    // then navigate to that page
    ASPx.SchedulerGotoDate(cal, 'ctl00_contentMain_schedulerMain_viewNavigatorBlock_ctl00');
    ''' % (year, month - 1, day, 0)  # for some reason, calendar objects represent months starting with 0: January

    wait_for_page_load(timeout, browser.execute_script, js_source)

    # check results
    loaded_ymd = get_date()
    assert (year, month, day) == loaded_ymd, 'Failed to load the requested date.'


def get_events():
    """
    Scrape the list of events from the current page.

    Returns
    -------
    parsed_events : list
        List of events.
        Each event is a dict with keys 'start', 'end', and 'info'.
        'start' and 'end' are datetime objects corresponding to start and end times, respectively.
        'info' is the textual description of the event.
    """

    # get the element containing all elements_in_schedule
    event_container = browser.find_element_by_id(
        'ctl00_contentMain_schedulerMain_containerBlock_verticalContainerappointmentLayer'
    )

    # get all child objects
    elements_in_schedule = event_container.find_elements_by_xpath('.//*')

    # get actual events
    events = [elem for elem in elements_in_schedule if elem.get_attribute('id').endswith('_appointmentDiv')]

    parsed_events = []

    # record the date along with event info
    date = get_date()
    year, month, day = date

    # scrape start and end time strings
    for event in events:
        # get all child objects
        elements_in_event = event.find_elements_by_xpath('.//*')

        # add in current date to start time, so we get a datetime object with all info in one place

        event_full_text = event.get_attribute('innerText')

        start_times = [elem for elem in elements_in_event if elem.get_attribute('id').endswith('_lblStartTime')]
        assert len(start_times) == 1, 'Could not uniquely determine start time for event `%s`.' % event_full_text
        start_time_str = '%d-%d-%d ' % date + start_times[0].get_attribute('innerText')

        end_times = [elem for elem in elements_in_event if elem.get_attribute('id').endswith('_lblEndTime')]
        assert len(end_times) == 1, 'Could not uniquely determine end time for event `%s`.' % event_full_text
        end_time_str = '%d-%d-%d ' % date + end_times[0].get_attribute('innerText')

        info = [elem for elem in elements_in_event if elem.get_attribute('id').endswith('_lblTitle')]
        assert len(info) == 1, 'Could not uniquely determine description for event `%s`.' % event_full_text
        info = info[0].get_attribute('innerText')

        # make datetime objects to parse start and end times
        start_time = datetime.datetime.strptime(start_time_str, '%Y-%m-%d %I:%M %p-')
        end_time = datetime.datetime.strptime(end_time_str, '%Y-%m-%d %I:%M %p')

        parsed_events.append((year, month, day, start_time.isoformat(), end_time.isoformat(), info))

    return parsed_events


def nav_to_url(url):
    """
    Ask the browser to fetch the page located at url.

    Parameters
    ----------
    url : str
        URL of page.
    """

    browser.get(url)


def nav_to_local_file(filename):
    """
    Ask the browser to fetch the page located at the specified filename.

    Parameters
    ----------
    filename : str
        Filename of page to fetch.
    """

    url = urlparse.urljoin('file:', urllib.pathname2url(os.path.abspath(filename)))
    nav_to_url(url)


def export_page_to_file(filename):
    """
    Utility function that saves the current page (just DOM and HTML) to file.
    Can be loaded into selenium again with nav_to_local_file(filename).

    Parameters
    ----------
    filename : str
        Name of file to save source to.
    """

    with codecs.open(filename, 'w', 'utf-8') as fd:
        fd.write(browser.page_source)

def init_db(filename):
    """
    Utility function that initializes an SQLite database file, makes the events table, then closes it.
    Throws an sqlite3.Error if the table already exists in the database.

    Parameters
    ----------
    filename : str
        Name of the database file to use.

    """

    with sqlite3.connect(filename) as con:
        c = con.cursor()

        rows = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name='events' OR name='log');")
        if len(list(rows)) > 0:
            raise sqlite3.Error, 'Table `events` already exists.'

        # make table for scheduled events
        # database columns
        # year, month, day, start time, end time, description
        c.execute(
            """
            CREATE TABLE events
            (year integer, month integer, day integer, start_time text, end_time text, description text)
            """
        )

        # make table logging when daily schedule was last updated
        # database columns
        # day in schedule, time last updated
        c.execute(
            """
            CREATE TABLE log
            (sched_day text, mtime text)
            """
        )

def update_day(con, year, month, day, event_tuples):
    """
    Replace all events currently in the database for a current date with the supplied event data.

    Note that rollback() is called, so any uncommitted changes will be dropped at the beginning of this function.

    Parameters
    ----------
    con : sqlite3.Connection
        Connection to an open database.
    year, month, day : int, int, int
        Date being updated.
    event_tuples : list of row tuples for the events table
        Events to insert in the database.
    """

    # make sure nothing gets committed that wasn't performed by this function
    con.rollback()

    c = con.cursor()

    if len(event_tuples) > 0:
        # check that all events are from one day
        same_year = [year == e[0] for e in event_tuples]
        same_month = [month == e[1] for e in event_tuples]
        same_day = [day == e[2] for e in event_tuples]

        assert all(same_year) and all(same_month) and all(same_day)

    # clear out old rows
    c.execute('DELETE FROM events WHERE year=? AND month=? and day=?', (year, month, day))

    # add current events in
    c.executemany('INSERT INTO events VALUES (?,?,?, ?,?,?)', event_tuples)

    con.commit()

if __name__ == '__main__':
    main()
