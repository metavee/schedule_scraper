import datetime
import time

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException


def main():
    nav_to_date(2018, 6, 15)
    print get_date()

    browser.quit()


# options
# timeout interval (seconds)
default_timeout = 59.

# open the page
browser = webdriver.Chrome()
page_url_stub = 'https://nike.uwaterloo.ca/FacilityScheduling/FacilitySchedule.aspx?FacilityId='
pac_pool_id = '5d72208a-069d-4931-aaa6-9527346efc6f'
browser.get(page_url_stub + pac_pool_id)
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


def nav_to_date(year, month, day):
    """
    Navigate the page to the schedule for a particular date.

    Date must fall within a range between today and two years from today.

    Parameters
    ----------
    year : int
    month : int
    day : int
    """

    today = datetime.date.today()
    if year < today.year or (year == today.year and month < today.month) or \
            (year == today.year and month == today.month and day < today.day):
        raise ValueError('Date must fall between today and two years from today.')
    if year > today.year + 2 or (year == today.year + 2 and month > today.month) or \
            (year == today.year + 2 and month == today.month and day >= today.day):
        raise ValueError('Date must fall between today and two years from today.')

    js_source = '''
    // first, create a fake calendar object
    var cal = {};
    cal.GetValue = function() {return new Date(%d, %d, %d, %d);};

    // then navigate to that page
    ASPx.SchedulerGotoDate(cal, 'ctl00_contentMain_schedulerMain_viewNavigatorBlock_ctl00');
    ''' % (year, month - 1, day, 0)  # for some reason, calendar objects represent months starting with 0: January

    wait_for_page_load(default_timeout, browser.execute_script, js_source)

    # check results
    loaded_ymd = get_date()
    assert (year, month, day) == loaded_ymd, 'Failed to load the requested date.'

if __name__ == '__main__':
    main()
