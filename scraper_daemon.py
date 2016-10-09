"""
Background service/daemon which periodically scrapes the schedule.
"""

from collections import defaultdict
import datetime
import os
import sqlite3
import time

import daemon

import schedule_scraper as scsc

# if False, run a headless browser, and run program on a background service via daemon
debug_mode = True

# how many minutes to oversleep, to ensure that there is stuff to do after waking up
sleep_buffer = 5.

db_fn = 'test08.db'

# Rules describing when to update which day's schedule.
# Applies to a range of days, counted relative to today.
# 'period' specifies update frequency, in minutes.
rules = [
    {
        # update upcoming 2 weeks every hour
        'start': 0,
        'end': 13,
        'period': 60
    },
    # {
    #     # update the following 2 weeks every 8 hours
    #     'start': 14,
    #     'end': 27,
    #     'period': 8*60
    # },
    # {
    #     # update the following month every 25 hours
    #     'start': 28,
    #     'end': 31*2,
    #     'period': 25*60
    # }
]

def maintain_schedules(db_fn, rules, sleep_buffer=5.):
    """
    Update the schedules periodically.

    Parameters
    ----------
    db_fn : str
        Name of database file to use.
    rules : list
        List of rules describing update frequency for different spans of dates.
    sleep_buffer : float
        Amount of time to oversleep, in minutes.
    """

    if not os.path.exists(db_fn):
        scsc.init_db(db_fn)

    scsc.init_browser(debug_mode)
    scsc.nav_to_url(scsc.page_url_stub + scsc.pac_pool_id)

    while True:
        wakeup_dt = datetime.datetime.now()
        print 'The current time is %s.' % wakeup_dt.strftime(scsc.datetime_fmt)

        # run updates
        minutes_left = update(db_fn, rules)

        print 'Sleep interval: %d minutes.' % int(minutes_left)
        print 'Should wake up at %s.' % (
        (datetime.datetime.now() + datetime.timedelta(minutes=minutes_left)).strftime(scsc.datetime_fmt))

        time.sleep(minutes_left * 60 + sleep_buffer)
        print 'Done sleeping.'


def update(db_fn, rules):
    """
    Update the schedule.

    Parameters
    ----------
    db_fn : str
        Name of database file to use.
    rules : list
        List of rules describing update frequency for different spans of dates.

    Returns
    -------
    minutes_left : float
        Number of minutes between now and the next time the schedule needs to be updated.
    """

    con = sqlite3.connect(db_fn)

    # Time to wake up to do the next update.
    # Update this value later.
    next_wakeup_time = datetime.datetime.now() + datetime.timedelta(minutes=rules[0]['period'])

    for rule in rules:
        # list of days that this rule applies to
        dates = get_dates(rule)

        # Read mtime of each day from database, and store next update time here.
        next_updates = get_update_times(rule, con)

        for date in dates:
            datestr = date.strftime(scsc.date_fmt)
            if next_updates[date] < datetime.datetime.now():
                print '%s needs update.' % datestr
                scsc.nav_to_date(date.year, date.month, date.day)
                events = scsc.get_events()
                scsc.update_day(con, date.year, date.month, date.day, events)
                print 'Done'
            else:
                print '%s does not need update until %s.' % (datestr, next_updates[date])
                next_wakeup_time = min(next_wakeup_time, next_updates[date])

    clear_old_rows(con)

    con.close()

    minutes_left = (next_wakeup_time - datetime.datetime.now()).total_seconds() / 60

    return minutes_left


def get_dates(rule):
    """
    Returns a list of date objects that the rule applies to.
    """

    return [datetime.date.today() + datetime.timedelta(delta) for delta in range(rule['start'], rule['end'])]


def get_update_times(rule, con):
    """
    Get the times when each day in a rule should get updated next.

    Parameters
    ----------
    rule
        Rule describing update frequency for different spans of dates.
    con : sqlite3 connection
        Connection to database

    Returns
    -------
    next_updates : defaultdict
        Dictionary, keyed with date objects, containing times when that date should get updated.
    """

    c = con.cursor()

    max_interval = datetime.timedelta(minutes=rule['period'])

    # get update log from database
    start = (datetime.timedelta(rule['start']) + datetime.date.today()).strftime(scsc.date_fmt)
    end = (datetime.timedelta(rule['end']) + datetime.date.today()).strftime(scsc.date_fmt)

    rows = c.execute(
        """
        SELECT * FROM log
        WHERE date(sched_day) >= date(?)
          AND date(sched_day) <= date(?)
        """, (start, end)
    )

    # dictionary listing the next time a given day's schedule should be updated
    # if there's no record yet in the database, set next update time in the past to force update
    next_updates = defaultdict(lambda: datetime.datetime.now() - datetime.timedelta(1))

    for r in rows:
        sched_day = datetime.datetime.strptime(r[0], scsc.date_fmt).date()
        mtime = datetime.datetime.strptime(r[-1], scsc.datetime_fmt)
        next_updates[sched_day] = mtime + max_interval

    return next_updates

def clear_old_rows(con):
    """
    Delete old rows from the update log in the database, where old is anything before today.
    """
    todaystr = datetime.date.today().strftime(scsc.date_fmt)

    con.rollback()
    c = con.cursor()
    c.execute('DELETE FROM log WHERE date(sched_day) < date(?)', (todaystr,))
    con.commit()

if __name__ == '__main__':
    if debug_mode:
        maintain_schedules(db_fn, rules, sleep_buffer)
    else:
        with daemon.DaemonContext(working_directory='.', stdout=open('./scsc_stdout.log', 'a'), stderr=open('./scsc_stderr.log', 'a')):
            maintain_schedules(db_fn, rules, sleep_buffer)