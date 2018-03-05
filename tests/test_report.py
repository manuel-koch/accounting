import unittest
import os
import datetime

from accounting.core.core import Database, Account, Transaction, Item
from accounting.report import Report, ItemGroupingByDateRange, ReportTemplate
from accounting.core.dateutils import rangeDateFromTillByInterval, date_from_value
from accounting.core.dateutils import INTERVAL_DAILY, INTERVAL_WEEKLY, INTERVAL_MONTHLY, INTERVAL_ANUALY


class TestReport(unittest.TestCase):
    dates = (date_from_value("2018-03-08"),
             date_from_value("2018-03-09"),
             date_from_value("2018-03-16"),
             date_from_value("2018-04-01"),
             date_from_value("2018-06-17"),
             date_from_value("2018-11-20"),
             date_from_value("2019-02-13"),
             date_from_value("2020-06-02"),
             )

    def _newItem(self, descr, val, trn, acc):
        i = Item(descr, val)
        trn += i
        i += acc
        return i

    def _newTransaction(self, date, descr):
        t = Transaction(date, descr)
        self._db += t
        return t

    def setUp(self):
        self._db = Database()
        accRoot = Account("Root")
        self._db += accRoot
        accFoo = Account("Foo")
        accRoot += accFoo
        accBar = Account("Bar")
        accRoot += accBar
        accTest = Account("Test")
        accRoot += accTest

        t = self._newTransaction(self.dates[0], "one")
        self._newItem("AAA", 2.5, t, accFoo)
        self._newItem("BBB", -2.5, t, accBar)

        t = self._newTransaction(self.dates[1], "two")
        self._newItem("CCC", -2, t, accRoot)
        self._newItem("DDD", 2, t, accTest)

        t = self._newTransaction(self.dates[2], "three")
        self._newItem(u"EEE", 4, t, accFoo)
        self._newItem(u"FFF", -4, t, accBar)

        t = self._newTransaction(self.dates[2], "four")
        self._newItem(u"GGG", 3, t, accFoo)
        self._newItem(u"HHH", -3, t, accBar)

        t = self._newTransaction(self.dates[3], "five")
        self._newItem(u"III", 5, t, accFoo)
        self._newItem(u"JJJ", -5, t, accTest)

        t = self._newTransaction(self.dates[4], "six")
        self._newItem(u"KKK", 5, t, accFoo)
        self._newItem(u"LLL", -5, t, accBar)

        t = self._newTransaction(self.dates[4], "seven")
        self._newItem(u"MMM", 7, t, accFoo)
        self._newItem(u"NNN", -7, t, accBar)

        t = self._newTransaction(self.dates[5], "eight")
        self._newItem(u"OOO", 1, t, accFoo)
        self._newItem(u"PPP", -1, t, accBar)

        t = self._newTransaction(self.dates[6], "nine")
        self._newItem(u"QQQ", 1, t, accTest)
        self._newItem(u"RRR", -1, t, accBar)

        t = self._newTransaction(self.dates[7], "ten")
        self._newItem(u"SSS", 1, t, accFoo)
        self._newItem(u"TTT", -1, t, accBar)

    def tearDown(self):
        self._db = None

    def test_account_daily(self):
        fromDate, tillDate = rangeDateFromTillByInterval(self.dates[0], self.dates[0], INTERVAL_DAILY)
        report = Report(self._db, fromDate, tillDate)
        report += self._db["Root/Test"]
        items = [i.descr for i in report.items]
        self.assertSetEqual(set(), set(items))

        fromDate, tillDate = rangeDateFromTillByInterval(self.dates[0], self.dates[0], INTERVAL_DAILY)
        report = Report(self._db, fromDate, tillDate)
        report += self._db["Root/Foo"]
        items = [i.descr for i in report.items]
        self.assertSetEqual({'AAA'}, set(items))

        fromDate, tillDate = rangeDateFromTillByInterval(self.dates[1], self.dates[2], INTERVAL_DAILY)
        report = Report(self._db, fromDate, tillDate)
        report += self._db["Root/Foo"]
        items = [i.descr for i in report.items]
        self.assertSetEqual({'EEE', 'GGG'}, set(items))

        fromDate, tillDate = rangeDateFromTillByInterval(self.dates[0], self.dates[3], INTERVAL_DAILY)
        report = Report(self._db, fromDate, tillDate)
        report += self._db["Root/Foo"]
        report += self._db["Root/Bar"]
        items = [i.descr for i in report.items]
        self.assertSetEqual({'AAA', 'BBB', 'EEE', 'FFF', 'GGG', 'HHH', 'III'}, set(items))

    def test_account_and_children_daily(self):
        fromDate, tillDate = rangeDateFromTillByInterval(self.dates[0], self.dates[2], INTERVAL_DAILY)
        report = Report(self._db, fromDate, tillDate)
        report += self._db["Root"]
        items = [i.descr for i in report.items]
        self.assertSetEqual({'AAA', 'BBB', 'CCC', 'DDD', 'EEE', 'FFF', 'GGG', 'HHH'}, set(items))

        fromDate, tillDate = rangeDateFromTillByInterval(self.dates[0], self.dates[3], INTERVAL_DAILY)
        report = Report(self._db, fromDate, tillDate + datetime.timedelta(days=1))
        report += self._db["Root"]
        items = [i.descr for i in report.items]
        self.assertSetEqual({'AAA', 'BBB', 'CCC', 'DDD', 'EEE', 'FFF', 'GGG', 'HHH', 'III', 'JJJ'}, set(items))

    def test_accounts_by_week(self):
        fromDate, tillDate = rangeDateFromTillByInterval(self.dates[0], self.dates[0], INTERVAL_WEEKLY)
        self.assertEqual(datetime.timedelta(days=6), tillDate - fromDate)

        report = Report(self._db, fromDate, tillDate)
        report += self._db["Root/Foo"]
        items = [i.descr for i in report.items]
        self.assertSetEqual({'AAA'}, set(items))

        grp = ItemGroupingByDateRange(fromDate, tillDate, INTERVAL_WEEKLY)
        grp += report

        date_ranges = list(grp.groups())
        self.assertEqual(1, len(date_ranges))
        items_per_data_ranges = [list(grp.groupItems(date_range)) for date_range in date_ranges]
        items_per_data_ranges = [[i.descr for i in items] for items in items_per_data_ranges]
        self.assertSetEqual({'AAA'}, set(items_per_data_ranges[0]))

        fromDate, tillDate = rangeDateFromTillByInterval(self.dates[0], self.dates[2], INTERVAL_WEEKLY)
        self.assertEqual(datetime.timedelta(days=13), tillDate - fromDate)

        report = Report(self._db, fromDate, tillDate)
        report += self._db["Root/Foo"]
        items = [i.descr for i in report.items]
        self.assertSetEqual({'AAA', 'EEE', 'GGG'}, set(items))

        grp = ItemGroupingByDateRange(fromDate, tillDate, INTERVAL_WEEKLY)
        grp += report

        date_ranges = list(grp.groups())
        self.assertEqual(2, len(date_ranges))
        items_per_data_ranges = [list(grp.groupItems(date_range)) for date_range in date_ranges]
        items_per_data_ranges = [[i.descr for i in items] for items in items_per_data_ranges]
        self.assertSetEqual({'AAA'}, set(items_per_data_ranges[0]))
        self.assertSetEqual({'EEE', 'GGG'}, set(items_per_data_ranges[1]))

    def test_05_accounts_by_month(self):
        fromDate, tillDate = rangeDateFromTillByInterval(self.dates[0], self.dates[0], INTERVAL_MONTHLY)
        self.assertEqual(datetime.timedelta(days=30), tillDate - fromDate)

        report = Report(self._db, fromDate, tillDate)
        report += self._db["Root/Foo"]
        items = [i.descr for i in report.items]
        self.assertSetEqual({'AAA', 'EEE', 'GGG'}, set(items))

        grp = ItemGroupingByDateRange(fromDate, tillDate, INTERVAL_MONTHLY)
        grp += report

        date_ranges = list(grp.groups())
        self.assertEqual(1, len(date_ranges))
        items_per_data_ranges = [list(grp.groupItems(date_range)) for date_range in date_ranges]
        items_per_data_ranges = [[i.descr for i in items] for items in items_per_data_ranges]
        self.assertSetEqual({'AAA', 'EEE', 'GGG'}, set(items_per_data_ranges[0]))

        fromDate, tillDate = rangeDateFromTillByInterval(self.dates[0], self.dates[3], INTERVAL_MONTHLY)
        self.assertEqual(datetime.timedelta(days=60), tillDate - fromDate)

        report = Report(self._db, fromDate, tillDate)
        report += self._db["Root/Foo"]
        items = [i.descr for i in report.items]
        self.assertSetEqual({'AAA', 'EEE', 'GGG', 'III'}, set(items))

        grp = ItemGroupingByDateRange(fromDate, tillDate, INTERVAL_MONTHLY)
        grp += report

        date_ranges = list(grp.groups())
        self.assertEqual(2, len(date_ranges))
        items_per_data_ranges = [list(grp.groupItems(date_range)) for date_range in date_ranges]
        items_per_data_ranges = [[i.descr for i in items] for items in items_per_data_ranges]
        self.assertSetEqual({'AAA', 'EEE', 'GGG'}, set(items_per_data_ranges[0]))
        self.assertSetEqual({'III'}, set(items_per_data_ranges[1]))

    def test_06_accounts_by_year(self):
        fromDate, tillDate = rangeDateFromTillByInterval(self.dates[0], self.dates[0], INTERVAL_ANUALY)
        self.assertEqual(datetime.timedelta(days=364), tillDate - fromDate)

        report = Report(self._db, fromDate, tillDate)
        report += self._db["Root/Bar"]
        items = [i.descr for i in report.items]
        self.assertSetEqual({'BBB', 'FFF', 'HHH', 'LLL', 'NNN', 'PPP'}, set(items))

        grp = ItemGroupingByDateRange(fromDate, tillDate, INTERVAL_ANUALY)
        grp += report

        date_ranges = list(grp.groups())
        self.assertEqual(1, len(date_ranges))
        items_per_data_ranges = [list(grp.groupItems(date_range)) for date_range in date_ranges]
        items_per_data_ranges = [[i.descr for i in items] for items in items_per_data_ranges]
        self.assertSetEqual({'BBB', 'FFF', 'HHH', 'LLL', 'NNN', 'PPP'}, set(items_per_data_ranges[0]))

        fromDate, tillDate = rangeDateFromTillByInterval(self.dates[0], self.dates[6], INTERVAL_ANUALY)
        self.assertEqual(datetime.timedelta(days=729), tillDate - fromDate)

        report = Report(self._db, fromDate, tillDate)
        report += self._db["Root/Bar"]
        items = [i.descr for i in report.items]
        self.assertSetEqual({'BBB', 'FFF', 'HHH', 'LLL', 'NNN', 'PPP', 'RRR'}, set(items))

        grp = ItemGroupingByDateRange(fromDate, tillDate, INTERVAL_ANUALY)
        grp += report

        date_ranges = list(grp.groups())
        self.assertEqual(2, len(date_ranges))
        items_per_data_ranges = [list(grp.groupItems(date_range)) for date_range in date_ranges]
        items_per_data_ranges = [[i.descr for i in items] for items in items_per_data_ranges]
        self.assertSetEqual({'BBB', 'FFF', 'HHH', 'LLL', 'NNN', 'PPP'}, set(items_per_data_ranges[0]))
        self.assertSetEqual({'RRR'}, set(items_per_data_ranges[1]))

    def test_08_pie_template(self):
        fromDate, tillDate = rangeDateFromTillByInterval(self.dates[0], self.dates[0], INTERVAL_MONTHLY)
        report = Report(self._db, fromDate, tillDate)
        report += self._db["Root/Bar"]
        report_template_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "accounting", "templates"))
        report_template_name = "report_monthly_list_grouped_pct.accrep"
        template = ReportTemplate(report_template_dir, report_template_name)
        html = template.render(report)
        html_path = os.path.join(report_template_dir, os.path.splitext(report_template_name)[0] + ".html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)


if __name__ == "__main__":
    unittest.main()
