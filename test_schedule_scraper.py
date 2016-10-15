import datetime
import os
from unittest import TestCase

import sqlite3

import schedule_scraper as scsc

import scraper_daemon as sd

class TestScraperDaemon(TestCase):

    # test that clear_old_rows works
    # test that update returns something reasonable for the next update time
        # this may involve stubbing out nav_to_date and update_day
    # test that get_update_times returns correct update times

    def test_get_dates(self):
        """
        Test basic functionality of get_dates, namely that it returns the right list of dates for a rule.
        """

        today = datetime.date.today()
        delta = lambda d: datetime.timedelta(days=d)

        rule1 = {
            'start': 0,
            'end': 2,
            'period': 60
        }

        dates1 = sd.get_dates(rule1)
        expected1 = [today, today + delta(1), today + delta(2)]

        self.assertEqual(dates1, expected1)

        rule2 = {
            'start': 1,
            'end': 10,
            'period': 60
        }
        dates2 = sd.get_dates(rule2)
        self.assertEqual(today + delta(1), dates2[0])
        self.assertEqual(dates2[-1] - today, delta(10))
        self.assertEqual(len(dates2), 10)


class TestArchivedPages(TestCase):

    """
    Tests running on offline resources.
    Kept separate from other tests for speed purposes.

    Also, since they're offline, they will always be reachable, and the results will always be known.
    """

    file_20160921 = os.path.join('test_resources', '20160921_schedule.html')
    file_20170902 = os.path.join('test_resources', '20170902_schedule.html')

    @classmethod
    def setUpClass(cls):
        scsc.init_browser()

    @classmethod
    def tearDownClass(cls):
        scsc.browser.quit()

    def test_get_date(self):
        """
        Load a page with a known date, and ensure that it can be read correctly.
        """

        scsc.nav_to_local_file(self.file_20160921)
        self.assertEqual((2016, 9, 21), scsc.get_date())

    def test_get_events_empty(self):
        """
        Load a page with no events listed, and ensure that it is correctly parsed.
        """

        scsc.nav_to_local_file(self.file_20170902)
        events = scsc.get_events()
        self.assertEqual(len(events), 0)

    def test_get_events(self):
        """
        Load a page with many events, some overlapping in time, and ensure that it is correctly parsed.
        """

        scsc.nav_to_local_file(self.file_20160921)
        events = scsc.get_events()

        # check that the overall number of events is correct
        self.assertEqual(len(events), 11)

        # look at a few events
        ev4 = events[4]
        self.assertEqual(ev4[0:3], (2016, 9, 21))
        start_time = datetime.datetime(2016, 9, 21, 13, 0).strftime(scsc.datetime_fmt)
        end_time = datetime.datetime(2016, 9, 21, 15, 0).strftime(scsc.datetime_fmt)
        self.assertEqual(ev4[3], start_time)
        self.assertEqual(ev4[4], end_time)
        self.assertEqual(ev4[5], 'Subject: Varsity Swimming')

        ev5 = events[5]
        self.assertEqual(ev5[0:3], (2016, 9, 21))
        start_time = datetime.datetime(2016, 9, 21, 13, 0).strftime(scsc.datetime_fmt)
        end_time = datetime.datetime(2016, 9, 21, 14, 0).strftime(scsc.datetime_fmt)
        self.assertEqual(ev5[3], start_time)
        self.assertEqual(ev5[4], end_time)
        self.assertEqual(ev5[5], 'Course: Fall 2016 - Fitness Swimmer - Co-ed - 10 classes - Fit Swim - Wed')

    def test_update_day(self):
        """
        Test that schedule info is properly added to the database events and log tables.
        """

        # prep database
        con = sqlite3.connect(':memory:')
        scsc.init_db_con(con)
        c = con.cursor()

        # put some pre-existing events in
        old_events = [
            (2016, 9, 21, '2016-09-21 06:00:00', '2016-09-21 08:00:00', 'description 1'),
            (2016, 10, 16, '2016-10-16 06:00:00', '2016-10-16 08:00:00', 'description 2'),
            (2016, 10, 17, '2016-10-17 06:00:00', '2016-10-17 08:00:00', 'description 3')
        ]
        for ev in old_events:
            c.execute('INSERT INTO events VALUES (?, ?, ?, ?, ?, ?)', ev)

        con.commit()

        # run update schedule on day and make sure new entry is added, and old entry is overwritten
        scsc.nav_to_local_file(self.file_20160921)
        events = scsc.get_events()

        # get lower and upper bound of timestamp for update_day
        mtime_lower = datetime.datetime.now()
        scsc.update_day(con, 2016, 9, 21, events)
        mtime_upper = datetime.datetime.now()

        # check events table for this day
        rows = c.execute(
            """
            SELECT * FROM events
            WHERE year = ?
              AND month = ?
              AND day = ?
            """, (2016, 9, 21)
        )

        for i, r in enumerate(rows):
            # make sure pre-existing event was cleared out
            self.assertNotEqual(r[5], 'description 1')

            # check that particular event got added
            if i == 4:
                self.assertEqual(r[0:3], (2016, 9, 21))
                start_time = datetime.datetime(2016, 9, 21, 13, 0).strftime(scsc.datetime_fmt)
                end_time = datetime.datetime(2016, 9, 21, 15, 0).strftime(scsc.datetime_fmt)
                self.assertEqual(r[3], start_time)
                self.assertEqual(r[4], end_time)
                self.assertEqual(r[5], 'Subject: Varsity Swimming')

        # make sure this update is reflected in the log
        rows = c.execute(
            """
            SELECT mtime FROM log
            WHERE date(sched_day) = date(?)
            """, ('2016-09-21',)
        )

        # mtime should fall between mtime_lower and mtime_upper
        # mtime in the log doesn't store microseconds, so there is some loss of precision
        # drop microseconds from mtime_upper and mtime_lower to resolve
        mtime_lower -= datetime.timedelta(microseconds=mtime_lower.microsecond)
        mtime_upper -= datetime.timedelta(microseconds=mtime_upper.microsecond)
        mtime = datetime.datetime.strptime(rows.next()[0], scsc.datetime_fmt)
        self.assertLessEqual(mtime_lower, mtime)
        self.assertGreaterEqual(mtime_upper, mtime)

        # run the update again, and make sure there are no duplicate log entries for this day
        scsc.update_day(con, 2016, 9, 21, events)
        rows = c.execute(
            """
            SELECT mtime FROM log
            WHERE date(sched_day) = date(?)
            """, ('2016-09-21',)
        )
        self.assertEqual(len(list(rows)), 1)

        # test that events from other days were not disturbed
        rows = c.execute(
            """
            SELECT * FROM events
            WHERE year = ?
              AND month = ?
            """, (2016, 10)
        )
        self.assertEqual(rows.next(), old_events[1])
        self.assertEqual(rows.next(), old_events[2])



class TestLiveSite(TestCase):

    """
    Tests running on live website.
    These tests can be quite slow, due to the loading times on the server.
    """

    @classmethod
    def setUpClass(cls):
        scsc.init_browser()
        scsc.nav_to_url(scsc.page_url_stub + scsc.pac_pool_id)

    @classmethod
    def tearDownClass(cls):
        scsc.browser.quit()

    def test_nav_to_date_invalid_date(self):
        # plug in an invalid date to see if error is raised
        self.assertRaises(ValueError, scsc.nav_to_date, 2016, 20, 60)

        # try navigating to dates outside of valid range to see if error is raised
        today = datetime.date.today()
        yesterday = today + datetime.timedelta(-1)
        year, month, day = yesterday.year, yesterday.month, yesterday.day

        self.assertRaises(ValueError, scsc.nav_to_date, year, month, day)
        year_from_tomorrow = today + datetime.timedelta(2*365 + 1)
        year, month, day = year_from_tomorrow.year, year_from_tomorrow.month, year_from_tomorrow.day
        self.assertRaises(ValueError, scsc.nav_to_date, year, month, day)

    def test_nav_to_date(self):
        # try navigating to a week from today
        today = datetime.date.today()
        today_plus_7 = today + datetime.timedelta(7)
        year, month, day = today_plus_7.year, today_plus_7.month, today_plus_7.day
        scsc.nav_to_date(year, month, day)
        self.assertEqual((year, month, day), scsc.get_date())

        # navigate back to today
        year, month, day = today.year, today.month, today.day
        scsc.nav_to_date(year, month, day)
        self.assertEqual((year, month, day), scsc.get_date())
