import unittest
import os
import datetime
import time
import re
from io import BytesIO
from lxml import etree
import tempfile

from accounting.core.core import Database, Account, Transaction, Item


class TestStructure(unittest.TestCase):

    def test_transaction(self):
        db = Database()
        acc = Account("Root")
        db += acc
        t = Transaction(datetime.date.today())
        db += t

    def test_item(self):
        db = Database()
        acc = Account("Root")
        db += acc
        t = Transaction(datetime.date.today())
        db += t

        i = Item("Hello World", 2.99)
        t += i
        i += acc

        i = Item("Foo Bar", 1)
        t += i
        i += acc


class TestXml(unittest.TestCase):

    def test_01_xml(self):
        db = Database()
        acc1 = Account("Root")
        db += acc1
        acc2 = Account("Foo")
        acc1 += acc2
        acc3 = Account("Bar")
        acc1 += acc3

        t = Transaction(datetime.date.today(), "bar")
        db += t

        i = Item("AAA", -2)
        t += i
        i += acc1
        i = Item("BBB", 2)
        t += i
        i += acc2

        t = Transaction(datetime.date.today() + datetime.timedelta(days=1), "foo")
        db += t
        i = Item("CCC", 2.99)
        t += i
        i += acc1
        i = Item("DDD", -2.99)
        i += acc3
        t += i

        t = Transaction(datetime.date.today() - datetime.timedelta(days=3), "Flix")
        db += t
        i = Item(u"EEE <>/\\!'\"§$%&/(){}", 4)
        t += i
        i += acc1
        i = Item(u"FFF öäüÖÄÜß", -4)
        t += i
        i += acc3

        # remove the date/time depending string
        datePatchRe = re.compile("^\s*<saved\s+datetime=\".+?\"\s*/>\s*$", re.MULTILINE)

        xml = etree.tostring(db.toXml(),
                             encoding="utf-8",
                             xml_declaration=True,
                             pretty_print=True).decode("utf-8")
        print(xml)
        xml = datePatchRe.sub("", xml)
        print(xml)
        db2 = Database.parseFromXml(etree.parse(BytesIO(xml.encode("utf-8"))).getroot())
        xml2 = etree.tostring(db2.toXml(),
                              encoding="utf-8",
                              xml_declaration=True,
                              pretty_print=True).decode("utf-8")
        print(xml2)
        xml2 = datePatchRe.sub("", xml2)
        self.assertEqual(xml, xml2, "xml differs")


class TestFile(unittest.TestCase):

    def setUp(self):
        self.temp_path = tempfile.mktemp(suffix=".accdb")

    def tearDown(self):
        try:
            if os.path.isfile(self.temp_path):
                os.unlink(self.temp_path)
        except:
            pass

    def test_01_save(self):
        db = Database()
        acc1 = Account("Root")
        db += acc1
        acc2 = Account("Foo")
        acc1 += acc2

        self.assertEqual(2, db.nofAccounts())
        account_names = set([a.fullname for a in db.getChildAccounts(recurse=False)])
        self.assertSetEqual({"Root"}, account_names)
        account_names = set([a.fullname for a in db.getChildAccounts(recurse=True)])
        self.assertSetEqual({"Root", "Root/Foo"}, account_names)

        db.save(self.temp_path)

        time.sleep(1)

        acc3 = Account("Bar")
        acc1 += acc3

        self.assertEqual(3, db.nofAccounts())
        account_names = set([a.fullname for a in db.getChildAccounts(recurse=False)])
        self.assertSetEqual({"Root"}, account_names)
        account_names = set([a.fullname for a in db.getChildAccounts(recurse=True)])
        self.assertSetEqual({"Root", "Root/Foo", "Root/Bar"}, account_names)

        db.save(self.temp_path)

        time.sleep(1)

        acc4 = Account("Hello World")
        acc3 += acc4

        self.assertEqual(4, db.nofAccounts())
        account_names = set([a.fullname for a in db.getChildAccounts(recurse=False)])
        self.assertSetEqual({"Root"}, account_names)
        account_names = set([a.fullname for a in db.getChildAccounts(recurse=True)])
        self.assertSetEqual({"Root", "Root/Foo", "Root/Bar", "Root/Bar/Hello World"}, account_names)

        db.save(self.temp_path)

        db2 = Database.load(self.temp_path)

        self.assertEqual(4, db2.nofAccounts())
        account_names = set([a.fullname for a in db2.getChildAccounts(recurse=False)])
        self.assertSetEqual({"Root"}, account_names)
        account_names = set([a.fullname for a in db2.getChildAccounts(recurse=True)])
        self.assertSetEqual({"Root", "Root/Foo", "Root/Bar", "Root/Bar/Hello World"}, account_names)


if __name__ == "__main__":
    unittest.main()
