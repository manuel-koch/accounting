import datetime
import unittest

from accounting.core.dateutils import date_from_value


class TestDateutils(unittest.TestCase):

    def test_date_from_value(self):
        self.assertEqual(date_from_value("2018-01-01"), datetime.date(year=2018, month=1, day=1))
        self.assertEqual(date_from_value(datetime.datetime(year=2018, month=1, day=1, hour=10, minute=5)),
                         datetime.datetime(year=2018, month=1, day=1, hour=10, minute=5).date())


if __name__ == "__main__":
    unittest.main()
