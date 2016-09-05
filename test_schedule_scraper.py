import datetime
from unittest import TestCase

import schedule_scraper as scsc


class Test_schedule_scraper(TestCase):

    @classmethod
    def setUpClass(cls):
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
