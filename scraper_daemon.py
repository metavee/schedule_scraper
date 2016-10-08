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

def maintain_schedules(db_fn, rules, sleep_buffer):
    if not os.path.exists(db_fn):
        scsc.init_db(db_fn)

    scsc.init_browser()
    scsc.nav_to_url(scsc.page_url_stub + scsc.pac_pool_id)

    while True:
        wakeup_dt = datetime.datetime.now()

        print 'The current time is %s.' % wakeup_dt.strftime(scsc.datetime_fmt)

        con = sqlite3.connect(db_fn)
        c = con.cursor()

        todaystr = datetime.date.today().strftime(scsc.date_fmt)


        # Time to wake up to do the next update.
        # Update this value later.
        next_wakeup_time = wakeup_dt + datetime.timedelta(minutes=rules[0]['period'])

        for rule in rules:

            # Read mtime of each day from database, and store next update time here.
            next_updates = {}

            start =  (datetime.timedelta(rule['start']) + datetime.date.today()).strftime(scsc.date_fmt)
            end =  (datetime.timedelta(rule['end']) + datetime.date.today()).strftime(scsc.date_fmt)

            rows = c.execute(
                """
                SELECT * FROM log
                WHERE date(sched_day) >= date(?)
                  AND date(sched_day) <= date(?)
                """, (start, end)
            )

            max_interval = datetime.timedelta(minutes=rule['period'])

            for r in rows:
                mtime = datetime.datetime.strptime(r[-1], scsc.datetime_fmt)

                # Caching elapsed_time might be out-of-date by a few minutes,
                # depending on how long it takes to get through the rule.
                # This is an acceptable level of error.
                next_updates[r[0]] =  mtime + max_interval

            for delta in range(rule['start'], rule['end']):
                dateobj = datetime.date.today() + datetime.timedelta(delta)
                datestr = dateobj.strftime(scsc.date_fmt)

                # Update if last modification was too long ago.
                # Days that are included in the rule but not found in database need to be updated.
                if datestr not in next_updates or next_updates[datestr] < wakeup_dt:
                    print '%s needs update.' % datestr
                    scsc.nav_to_date(dateobj.year, dateobj.month, dateobj.day)
                    events = scsc.get_events()
                    scsc.update_day(con, dateobj.year, dateobj.month, dateobj.day, events)
                    print 'Done'
                else:
                    print '%s does not need update until %s.' % (datestr, next_updates[datestr])
                    next_wakeup_time = min(next_wakeup_time, next_updates[datestr])

        # Clear old rows from database.
        c.execute('DELETE FROM log WHERE date(sched_day) < date(?)', (todaystr,))
        con.commit()

        con.close()

        minutes_left = (next_wakeup_time - datetime.datetime.now()).total_seconds() / 60 + sleep_buffer

        print 'Sleep interval: %d minutes.' % int(minutes_left)
        print 'Should wake up at %s.' % ((datetime.datetime.now() + datetime.timedelta(minutes=minutes_left)).strftime(scsc.datetime_fmt))

        time.sleep(minutes_left * 60)
        print 'Done sleeping.'

if __name__ == '__main__':
    if debug_mode:
        maintain_schedules(db_fn, rules, sleep_buffer)
    else:
        with daemon.DaemonContext(working_directory='.', stdout=open('./scsc_stdout.log', 'a'), stderr=open('./scsc_stderr.log', 'a')):
            maintain_schedules(db_fn, rules, sleep_buffer)