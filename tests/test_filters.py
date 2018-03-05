import unittest

from accounting.core.core import Account, Transaction, Item
from accounting.core.core import FilterLessOrEqualDate, FilterGreaterOrEqualDate
from accounting.core.core import FilterAccountsAndChildren


class TestFilters(unittest.TestCase):

    def testFilterByDate(self):
        f1 = FilterGreaterOrEqualDate("2013-07-01")
        f2 = FilterLessOrEqualDate("2013-07-31")
        f3 = f1 & f2

        t = Transaction("2013-07-07")
        i = Item()
        t += i
        self.assertTrue(f1.accepted(t))
        self.assertFalse(f1.rejected(t))

        self.assertTrue(f2.accepted(t))
        self.assertFalse(f2.rejected(t))

        self.assertTrue(f3.accepted(t))
        self.assertFalse(f3.rejected(t))

        self.assertTrue(f1.accepted(i))
        self.assertFalse(f1.rejected(i))

        self.assertTrue(f2.accepted(i))
        self.assertFalse(f2.rejected(i))

        self.assertTrue(f3.accepted(i))
        self.assertFalse(f3.rejected(i))

        t = Transaction("2013-08-07")
        i = Item()
        t += i

        self.assertTrue(f1.accepted(t))
        self.assertFalse(f1.rejected(t))

        self.assertFalse(f2.accepted(t))
        self.assertTrue(f2.rejected(t))

        self.assertFalse(f3.accepted(t))
        self.assertTrue(f3.rejected(t))

        self.assertTrue(f1.accepted(i))
        self.assertFalse(f1.rejected(i))

        self.assertFalse(f2.accepted(i))
        self.assertTrue(f2.rejected(i))

        self.assertFalse(f3.accepted(i))
        self.assertTrue(f3.rejected(i))

        t = Transaction("2013-06-07")
        i = Item()
        t += i

        self.assertFalse(f1.accepted(t))
        self.assertTrue(f1.rejected(t))

        self.assertTrue(f2.accepted(t))
        self.assertFalse(f2.rejected(t))

        self.assertFalse(f3.accepted(t))
        self.assertTrue(f3.rejected(t))

        self.assertFalse(f1.accepted(i))
        self.assertTrue(f1.rejected(i))

        self.assertTrue(f2.accepted(i))
        self.assertFalse(f2.rejected(i))

        self.assertFalse(f3.accepted(i))
        self.assertTrue(f3.rejected(i))

    def testFilterByAccount(self):
        i = Item()
        a1 = Account("Foo")
        i += a1
        f = FilterAccountsAndChildren(a1)
        self.assertTrue(f.accepted(i))

        a2 = Account("Bar")
        f = FilterAccountsAndChildren(a2, a1)
        self.assertTrue(f.accepted(i))

        a3 = Account("Hello")
        f = FilterAccountsAndChildren(a2, a3)
        self.assertFalse(f.accepted(i))


if __name__ == "__main__":
    unittest.main()
