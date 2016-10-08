"""
Background service/daemon which periodically scrapes the schedule.

process:
-start/wake up from sleep
-get current datetime
-get list of rules about when to update which schedule
-for each rule, get list of days it applies to, and time they were last updated
-check if an update is due
-run updates to schedule, and update the last-updated field
-clear old entries from log
-sleep until next update is needed
"""

import datetime
import os
import sqlite3
import time

import schedule_scraper as scsc

scsc.init_browser()
scsc.nav_to_url(scsc.page_url_stub + scsc.pac_pool_id)

db_fn = 'test08.db'
if not os.path.exists(db_fn):
    scsc.init_db(db_fn)

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

con = sqlite3.connect(db_fn)
c = con.cursor()

while True:

    wakeup_dt = datetime.datetime.now()

    # Time to sleep until the next update.
    # Update this value later.
    next_sleep_length = rules[0]['period']

    for rule in rules:
        next_sleep_length = min(next_sleep_length, rule['period'])

        # Read mtime of each day from database, and store time delta since last update here.
        elapsed_times = {}

        start =  (datetime.timedelta(rule['start']) + datetime.date.today()).isoformat()
        end =  (datetime.timedelta(rule['end']) + datetime.date.today()).isoformat()

        rows = c.execute(
            """
            SELECT * FROM log
            WHERE date(sched_day) >= date(?)
              AND date(sched_day) <= date(?)
            """, (start, end)
        )

        max_interval = datetime.timedelta(minutes=rule['period'])

        for r in rows:
            mtime = datetime.datetime.strptime(r[-1], '%Y-%m-%d %H:%M:%S')

            # Caching elapsed_time might be out-of-date by a few minutes,
            # depending on how long it takes to get through the rule.
            # This is an acceptable level of error.
            elapsed_times[r[0]] =  wakeup_dt - mtime

        for delta in range(rule['start'], rule['end']):
            dateobj = datetime.date.today() + datetime.timedelta(delta)
            datestr = dateobj.isoformat()

            # Update if last modification was too long ago.
            # Days that are included in the rule but not found in database need to be updated.
            if datestr not in elapsed_times or elapsed_times[datestr] > max_interval:
                print '%s needs update.' % datestr
                scsc.nav_to_date(dateobj.year, dateobj.month, dateobj.day)
                events = scsc.get_events()
                scsc.update_day(con, dateobj.year, dateobj.month, dateobj.day, events)
                print 'Done'
            else:
                print '%s does not need update.' % datestr
                minutes_left = (max_interval - elapsed_times[datestr]).total_seconds() / 60
                next_sleep_length = min(next_sleep_length, minutes_left)

    # Clear old rows from database.
    c.execute('DELETE FROM log WHERE date(sched_day) < date(?)', (datetime.date.today().isoformat(),))
    con.commit()

    con.close()

    print 'sleep interval: %d minutes' % int(next_sleep_length)

    time.sleep(next_sleep_length * 60)