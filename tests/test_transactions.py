# -*- coding: utf-8 -*-
'''
Created on 26.03.2013

@author: manuel
'''
import unittest
import datetime

from decimal import Decimal

from accounting.core.core import Database, Account, Transaction, Item


class TestTransactions(unittest.TestCase):

    def test_transactions(self):
        today = datetime.date.today()
        db = Database()
        acc1 = Account("A")
        db += acc1
        acc2 = Account("B")
        db += acc2

        t0 = Transaction(today, "B")
        db += t0
        i0 = Item("AA", 1)
        t0 += i0
        i0 += acc1
        i1 = Item("BB", -1)
        t0 += i1
        i1 += acc2

        t1 = Transaction(today + datetime.timedelta(days=1), "C")
        db += t1
        i2 = Item("CC", -2)
        t1 += i2
        i2 += acc1
        i3 = Item("DD", -2)
        t1 += i3
        i3 += acc2

        t2 = Transaction(today - datetime.timedelta(days=5), "A")
        db += t2
        i4 = Item("EE", -3)
        t2 += i4
        i4 += acc1
        i5 = Item("FF", -3)
        t2 += i5
        i5 += acc2

        expected_transactions = [t2, t0, t1]
        current_transactions = list(db.filterTransactions())
        self.assertListEqual(expected_transactions, current_transactions)

        t1.setDate(today - datetime.timedelta(days=1))

        expected_transactions = [t2, t1, t0]
        current_transactions = list(db.filterTransactions())
        self.assertListEqual(expected_transactions, current_transactions)

    def test_balanced(self):
        db = Database()
        asset = Account("Asset")
        db += asset
        debit = Account("Debit")
        db += asset

        t = Transaction(datetime.date.today())
        db += t

        i = Item("Hello World", 2)
        t += i
        i += asset

        self.assertEqual(Decimal("2.00"), t.getBalance())
        self.assertFalse(t.isBalanced())

        i = Item("Foo Bar", -1)
        t += i
        i += debit

        self.assertEqual(Decimal("1.00"), t.getBalance())
        self.assertFalse(t.isBalanced())

        i.setValue(-2)

        self.assertEqual(Decimal("0"), t.getBalance())
        self.assertTrue(t.isBalanced())


if __name__ == "__main__":
    unittest.main()
