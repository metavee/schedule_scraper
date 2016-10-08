import datetime
import os
from unittest import TestCase

import schedule_scraper as scsc

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
