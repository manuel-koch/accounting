import unittest
import datetime

from accounting.core.core import Database, Account, Transaction, Item


class TestAccounts(unittest.TestCase):

    def test_01_root(self):
        db = Database()
        acc = Account("Root")
        db += acc
        self.assertIn("Root", db)
        self.assertIsNotNone(db["Root"])
        self.assertNotIn("Foo", db)
        with self.assertRaises(KeyError):
            db["Foo"]

    def test_02_sub(self):
        db = Database()
        acc = Account("Root")
        db += acc
        sacc = Account("Sub")
        acc += sacc
        self.assertIn("Root/Sub", db)
        self.assertIsNotNone(db["Root/Sub"])
        self.assertNotIn("Root/Foo", db)
        with self.assertRaises(KeyError):
            db["Root/Foo"]

    def test_03_items(self):
        db = Database()
        acc1 = Account("A")
        db += acc1
        acc2 = Account("B")
        db += acc2

        t0 = Transaction(datetime.date.today())
        db += t0
        i0 = Item("AA", 1)
        t0 += i0
        i0 += acc1
        i1 = Item("BB", -1)
        t0 += i1
        i1 += acc2

        t1 = Transaction(datetime.date.today() + datetime.timedelta(days=1))
        db += t1
        i2 = Item("CC", -2)
        t1 += i2
        i2 += acc1
        i3 = Item("DD", -2)
        t1 += i3
        i3 += acc2

        expected_acc_items = [i0, i2]
        current_acc_items = list(acc1.filterItems())
        self.assertListEqual(expected_acc_items, current_acc_items)

        expected_acc_items = [i1, i3]
        current_acc_items = list(acc2.filterItems())
        self.assertListEqual(expected_acc_items, current_acc_items)

        t1.setDate(datetime.date.today() - datetime.timedelta(days=1))

        expected_acc_items = [i2, i0]
        current_acc_items = list(acc1.filterItems())
        self.assertListEqual(expected_acc_items, current_acc_items)

        expected_acc_items = [i3, i1]
        current_acc_items = list(acc2.filterItems())
        self.assertListEqual(expected_acc_items, current_acc_items)


if __name__ == "__main__":
    unittest.main()
