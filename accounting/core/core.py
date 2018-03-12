# -*- coding: utf-8 -*-
'''
Core functionality of accounting package.

@author: Manuel Koch
'''

import os
import shutil
import datetime
from decimal import Decimal
import itertools
import logging
from lxml import etree
from io import BytesIO
import zipfile

from PyQt5.QtCore import QObject, pyqtSignal

from accounting.core.value import to_decimal
from accounting.core.filter import Filter
from accounting.core.dateutils import date_from_value

LOGGER = logging.getLogger(__name__)


class DatabaseException(Exception):
    pass


class UnknownAccountException(DatabaseException):
    pass


class Item(object):
    """An item is a subset of a transaction."""

    def __init__(self, descr="", value=None, confirmed=False):
        """Construct item."""
        self._account = None
        self._transaction = None
        self._descr = ""
        self._value = Decimal(0)
        self._confirmed = False
        self.setDescr(descr)
        self.setValue(value)
        self.setConfirmed(confirmed)

    def __repr__(self, ):
        return "Item(descr={!r},value={!r},confirmed={!r})".format(self._descr, self._value, self._confirmed)

    def __float__(self):
        return self._value

    def __radd__(self, other):
        if isinstance(other, Decimal) or isinstance(other, int):
            return self._value + other
        else:
            raise TypeError("Expected Decimal or int")

    def __iadd__(self, other):
        """Add given instance to item."""
        if isinstance(other, Account):
            if other != self._account:
                if self._account:
                    self._account -= self
                self._account = other
                self._account += self
        elif isinstance(other, Transaction):
            if other != self._transaction:
                if self._transaction:
                    self._transaction -= self
                self._transaction = other
                self._transaction += self
        else:
            raise TypeError()
        return self

    def __isub__(self, other):
        """Remove given instance from item."""
        if isinstance(other, Account):
            if other == self._account:
                self._account = None
                other -= self
        elif isinstance(other, Transaction):
            if other == self._transaction:
                self._transaction = None
                other -= self
        else:
            raise TypeError()
        return self

    @property
    def descr(self):
        return self._descr

    def setDescr(self, descr):
        descr = str(descr)
        if descr != self._descr:
            self._descr = descr
            return True
        else:
            return False

    @property
    def value(self):
        return self._value

    @property
    def valueDerived(self):
        sign = -1 if self._account and self._account.typeDerived in [Account.TYPE_EXPENSE, Account.TYPE_PROFIT] else 1
        return self._value * sign

    def setValue(self, val):
        val = to_decimal(val)
        if val != self._value:
            self._value = val
            return True
        else:
            return False

    def setAsset(self, val):
        return self.setValue(to_decimal(val))

    def setDebit(self, val):
        return self.setValue(-to_decimal(val))

    @property
    def confirmed(self):
        return self._confirmed

    def setConfirmed(self, confirmed):
        if isinstance(confirmed, str):
            confirmed = confirmed.lower() in ["yes", "true"]
        confirmed = bool(confirmed)
        if confirmed != self._confirmed:
            self._confirmed = confirmed
            return True
        else:
            return False

    @property
    def db(self):
        """Get database instance."""
        if self._account:
            return self._account.db
        if self._transaction:
            return self._transaction.db
        return None

    @property
    def account(self):
        return self._account

    @property
    def accountFullname(self):
        if self._account:
            return self._account.fullname
        else:
            return u""

    @property
    def transaction(self):
        return self._transaction

    @property
    def date(self):
        if self._transaction:
            return self._transaction.date
        else:
            return None

    @staticmethod
    def parseFromXml(elem, transaction):
        for itemElem in elem.xpath("item"):
            v = to_decimal(itemElem.get("value"))
            d = itemElem.get("descr")
            c = itemElem.get("confirmed")
            item = Item(value=v, descr=d, confirmed=c)
            transaction += item
            a = itemElem.get("account")
            if not a in transaction.db:
                raise UnknownAccountException(a)
            account = transaction.db[a]
            account += item

    def toXml(self, root):
        elem = etree.SubElement(root, "item")
        elem.set("descr", self._descr)
        elem.set("value", str(self._value))
        elem.set("confirmed", str(self._confirmed))
        elem.set("account", self._account.fullname)
        return elem


class Transaction(object):
    """A transaction combines multiple items at a given date."""

    def __init__(self, date=None, descr=""):
        """Construct transaction."""
        date = date_from_value(date) if date else None
        if descr != None and not isinstance(descr, str):
            raise TypeError("descr must be a string")
        self._db = None
        self._date = date
        self._descr = descr
        self._items = []

    def __repr__(self):
        return "Transaction(date={!r},descr={!r})".format(self._date, self._descr)

    def __str__(self):
        return u"{} {}".format(self._date, self._descr)

    def __len__(self):
        return len(self._items)

    def __getitem__(self, key):
        return self._items[key]

    def __iter__(self):
        return iter(self._items)

    def __iadd__(self, other):
        """Add given instance to transaction."""
        if isinstance(other, Item):
            if not other in self._items:
                self._items += [other]
                other += self
        elif isinstance(other, Database):
            if other != self._db:
                if self._db:
                    self._db -= self
                self._db = other
                self._db += self
        else:
            raise TypeError()
        return self

    def __isub__(self, other):
        """Remove given instance from item."""
        if isinstance(other, Item):
            if other in self._items:
                self._items.remove(other)
                other -= self
        elif isinstance(other, Database):
            if other == self._db:
                self._db = None
                other -= self
        else:
            raise TypeError()
        return self

    @property
    def db(self):
        return self._db

    @property
    def date(self):
        return self._date

    def setDate(self, date):
        if date != None:
            if isinstance(date, datetime.datetime):
                date = date.date()
            elif isinstance(date, datetime.date):
                pass
            else:
                raise TypeError("Expected datetime or date")

        self._date = date
        if self._db:
            self._db.sortTransactions()
        return True

    @property
    def descr(self):
        return self._descr

    def setDescr(self, descr):
        try:
            self._descr = str(descr)
            return True
        except:
            return False

    def filterItems(self, filter_=None):
        """Get iterator for items matching given account(s)."""
        if filter_ is None:
            return iter(self._items)
        else:
            return itertools.filterfalse(filter_.rejected, self._items)

    def hasItems(self, filter_):
        """Return true if transaction has items for given account(s) or any item."""
        for dummyItem in self.filterItems(filter_):
            return True  # at least on item found
        return False

    def getBalance(self):
        """Return sum of all items of this transaction."""
        return sum([i.value for i in self._items])

    def isBalanced(self):
        """Returns true when items are balanced ( values distributed equally among accounts )."""
        return self.getBalance() == 0

    @staticmethod
    def parseFromXml(elem, db):
        transactionElements = elem.xpath("transaction")
        if not transactionElements:
            return
        LOGGER.debug("Parsing %d transactions..." % len(transactionElements))
        for transactionElem in transactionElements:
            dt = [int(x) for x in transactionElem.get("date").split("-")]
            dt = datetime.date(year=dt[0], month=dt[1], day=dt[2])
            d = transactionElem.get("descr")
            transaction = Transaction(date=dt, descr=d)
            db += transaction
            Item.parseFromXml(transactionElem, transaction)

    def toXml(self, root):
        if not self._items:
            return None
        elem = etree.SubElement(root, "transaction")
        elem.set("date", str(self._date))
        elem.set("descr", self._descr)
        for item in self._items:
            item.toXml(elem)
        return elem


class AccountTreeItem(QObject):
    """Generic class for tree hierarchy."""

    def __init__(self):
        """Construct a account tree instance."""
        super().__init__()
        self._parentAccount = None
        self._childAccounts = []

    def getRootAccount(self):
        """Return parent account of this account if any."""
        return self._parentAccount if self._parentAccount else self

    def hasParentAccount(self):
        """Return whether this account has a parent account."""
        return self._parentAccount is not None

    def getParentAccount(self):
        """Return parent account of this account if any."""
        return self._parentAccount

    def getChildAccounts(self, recurse=False):
        """Return list of child accounts."""
        if recurse:
            l = []
            for child in self._childAccounts:
                l += [child]
                l += child.getChildAccounts(True)
            return l
        else:
            return self._childAccounts[:]

    def hasChildAccount(self, child):
        """Return true when this account has given (grand) child account."""
        if child in self._childAccounts:
            return True
        for c in self._childAccounts:
            if c.hasChildAccount(child):
                return True
        return False

    def isSelfOrHasChildAccount(self, child):
        """Return true when given account is self or a child of self."""
        return self == child or self.hasChildAccount(child)

    def isChildAccount(self, parent):
        """Return true when this account is a (grand) child of given parent account."""
        if self._parentAccount == parent:
            return True
        if self._parentAccount:
            return self._parentAccount.isChildAccount(parent)
        else:
            return False


class Account(AccountTreeItem):
    """An account is the target/source of an item."""

    SEPARATOR = u"/"

    TYPE_UNKNOWN = 0
    TYPE_PROFIT = 1  # getting money from
    TYPE_EXPENSE = 2  # spending money on
    TYPE_ASSET = 3  # e.g. cash or bank account
    TYPE_LIABILITY = 4  # e.g. a credit card
    ALL_TYPES = {TYPE_UNKNOWN: "Unknown",
                 TYPE_PROFIT: "Profit",
                 TYPE_EXPENSE: "Expense",
                 TYPE_ASSET: "Asset",
                 TYPE_LIABILITY: "Liability"}
    ALL_TYPES_BY_NAME = {ALL_TYPES[TYPE_UNKNOWN]: TYPE_UNKNOWN,
                         ALL_TYPES[TYPE_PROFIT]: TYPE_PROFIT,
                         ALL_TYPES[TYPE_EXPENSE]: TYPE_EXPENSE,
                         ALL_TYPES[TYPE_ASSET]: TYPE_ASSET,
                         ALL_TYPES[TYPE_LIABILITY]: TYPE_LIABILITY}

    # signal emitted when name of account changed
    nameChanged = pyqtSignal(str)

    # signal emitted when type of account changed
    typeChanged = pyqtSignal(int)

    def __init__(self, name, type_=TYPE_UNKNOWN):
        """Construct category."""
        super().__init__()
        if Account.SEPARATOR in name:
            raise Exception("Invalid character in name")
        if type_ not in Account.ALL_TYPES:
            raise Exception("Invalid type")
        self._name = str(name)
        self._type = type_
        self._db = None

    def __repr__(self, ):
        return "Account(name={!r})".format(self.fullname)

    def __str__(self, ):
        return self._name

    def __getitem__(self, key):
        """Get sub account of given name."""
        if isinstance(key, str):
            parts = key.split(Account.SEPARATOR)
            for acc in self._childAccounts:
                if parts[0] == acc.name:
                    if len(parts) > 1:
                        return acc[Account.SEPARATOR.join(parts[1:])]
                    else:
                        return acc
        raise KeyError

    def __setitem__(self, key, value):
        """Set sub account of given name."""
        if not isinstance(value, Account):
            raise TypeError
        if isinstance(key, str):
            parts = key.split(Account.SEPARATOR)
            for idx, acc in enumerate(self._childAccounts):
                if parts[0] == acc.name:
                    if len(parts) > 1:
                        acc[Account.SEPARATOR.join(parts[1:])] = value
                        return
                    else:
                        self._childAccounts[idx] = value
                        return
        raise KeyError

    def __contains__(self, key):
        """Returns true when given key is this account or sub account of given name exists."""
        if isinstance(key, str):
            parts = key.split(Account.SEPARATOR)
            for acc in self._childAccounts:
                if parts[0] == acc.name:
                    if len(parts) > 1:
                        return Account.SEPARATOR.join(parts[1:]) in acc
                    else:
                        return True
        return False

    def __iadd__(self, other):
        """Add instance to account."""
        if isinstance(other, Item):
            other += self
        elif isinstance(other, Account):
            if not other in self._childAccounts:
                self._childAccounts += [other]
                other._parentAccount = self
        elif isinstance(other, Database):
            if other != self._db:
                self._db = other
                other += self
        else:
            raise TypeError()
        return self

    def __isub__(self, other):
        """Remove instance from account."""
        if isinstance(other, Item):
            other -= self
        elif isinstance(other, Account):
            if other in self._childAccounts:
                self._childAccounts.remove(other)
                other._parentAccount = None
        elif isinstance(other, Database):
            if self._db == other:
                db = self._db
                self._db = None
                db -= self
        else:
            raise TypeError()
        return self

    def filterItems(self, filter_=None):
        """Get iterator for items of current account matching given AND combined filters"""
        accFilter = FilterAccountsAndChildren(self)
        if filter_ is None:
            return self.db.filterItems(accFilter)
        else:
            return self.db.filterItems(accFilter & filter_)

    def filterTransactions(self, filter_=None):
        """Get iterator for transactions of current account matching given AND combined filters"""
        accFilter = FilterAccountsAndChildren(self)
        if filter_ is None:
            return self.db.filterTransactions(accFilter)
        else:
            return self.db.filterTransactions(accFilter & filter_)

    @property
    def name(self):
        return self._name

    def setName(self, newName):
        """Set name of this account."""
        if Account.SEPARATOR in newName:
            return False
        if self._parentAccount:
            if newName in self._parentAccount:
                return False
        elif self._db and newName in self._db:
            return False
        n = str(newName)
        if self._name != n:
            self._name = n
            self.nameChanged.emit(self._name)
        return True

    @property
    def fullname(self):
        if self._parentAccount:
            return self._parentAccount.fullname + Account.SEPARATOR + self._name
        else:
            return self._name

    @property
    def type(self):
        return self._type

    @property
    def typeDerived(self):
        if self._type == Account.TYPE_UNKNOWN:
            if self.hasParentAccount():
                return self.getParentAccount().typeDerived
            LOGGER.warning("Unknown derived type for {}".format(self.fullname))
        return self._type

    def setType(self, newType):
        """Set type of this account."""
        if not newType in Account.ALL_TYPES:
            raise TypeError("Invalid account type")
        if self._type != newType:
            self._type = newType
            self.typeChanged.emit(self._type)
        return True

    @property
    def db(self):
        if self._db:
            return self._db
        elif self._parentAccount:
            return self._parentAccount.db
        else:
            return None

    @staticmethod
    def parseFromXml(elem, db, parentAccount=None):
        accElements = elem.xpath("account")
        if not accElements:
            return
        LOGGER.debug("Parsing %d accounts..." % len(accElements))
        for accElem in accElements:
            t = accElem.get("type")
            t = Account.ALL_TYPES_BY_NAME.get(t, Account.TYPE_UNKNOWN)
            account = Account(name=accElem.get("name"), type_=t)
            if parentAccount:
                parentAccount += account
            else:
                db += account
            Account.parseFromXml(accElem, db, account)

    def toXml(self, root):
        elem = etree.SubElement(root, "account")
        elem.set("name", self._name)
        elem.set("type", Account.ALL_TYPES[self._type])
        for acc in self._childAccounts:
            acc.toXml(elem)
        return elem


class Database(AccountTreeItem):
    """A database holds accounts and transactions."""

    XML_VERSION = (1, 0)
    CURRENT_DB_NAME = "current.accdb"

    def __init__(self):
        """Construct database."""
        super().__init__()
        self._transactions = []
        self._parsing = False

    def nofTransactions(self):
        """Return number of transactions in database"""
        return len(self._transactions)

    def nofAccounts(self):
        """Return number of accounts in database"""
        return len(self.getChildAccounts(True))

    def __getitem__(self, key):
        """Get account by given name."""
        if isinstance(key, str):
            parts = key.split(Account.SEPARATOR)
            for acc in self._childAccounts:
                if parts[0] == acc.name:
                    if len(parts) > 1:
                        return acc[Account.SEPARATOR.join(parts[1:])]
                    else:
                        return acc
        raise KeyError

    def __setitem__(self, key, value):
        """Set account by given name."""
        if not isinstance(value, Account):
            raise TypeError
        if isinstance(key, str):
            parts = key.split(Account.SEPARATOR)
            for idx, acc in enumerate(self._childAccounts):
                if parts[0] == acc.name:
                    if len(parts) > 1:
                        acc[Account.SEPARATOR.join(parts[1:])] = value
                        return
                    else:
                        self._childAccounts[idx] = value
                        return
        raise KeyError

    def __contains__(self, key):
        """Return true when named account exists in database."""
        if isinstance(key, str):
            parts = key.split(Account.SEPARATOR)
            for acc in self._childAccounts:
                if parts[0] == acc.name:
                    if len(parts) > 1:
                        return Account.SEPARATOR.join(parts[1:]) in acc
                    else:
                        return True
        return False

    def __iadd__(self, other):
        """Add instance to database."""
        if isinstance(other, Account):
            if not other in self._childAccounts:
                self._childAccounts += [other]
                other += self
        elif isinstance(other, Transaction):
            if not other in self._transactions:
                self._transactions += [other]
                other += self
                if not self._parsing:
                    self.sortTransactions()
        else:
            raise TypeError()
        return self

    def __isub__(self, other):
        """Remove instance from database."""
        if isinstance(other, Account):
            if other in self._childAccounts:
                self._childAccounts.remove(other)
                other -= self
        elif isinstance(other, Transaction):
            if other in self._transactions:
                self._transactions.remove(other)
                other -= self
        else:
            raise TypeError()
        return self

    def sortTransactions(self):
        """Trigger sorting of transactions"""
        self._transactions.sort(key=lambda t: t.date)

    def filterTransactions(self, filter_=None):
        """Get iterator for transactions matching given filter"""
        if filter_ is None:
            return iter(self._transactions)
        else:
            return itertools.filterfalse(filter_.rejected, self._transactions)

    def filterItems(self, filter_=None):
        """Get iterator for items matching given filter"""
        trnIter = self.filterTransactions(filter_)
        trnItemsIter = map(lambda trn: trn.filterItems(filter_), trnIter)
        return itertools.chain.from_iterable(trnItemsIter)

    @staticmethod
    def parseFromXml(elem):
        if not elem.tag == "database":
            return None
        LOGGER.debug("Parsing database...")
        db = Database()
        try:
            db._parsing = True

            saved = elem.xpath("meta/saved/@datetime")
            saved = datetime.datetime.strptime(saved[0], "%Y-%m-%d %H:%M:%S") if saved else None
            LOGGER.debug("Saved on {}".format(saved or "?"))

            major = 0
            minor = 0
            if elem.xpath("meta/version"):
                major = int(elem.xpath("meta/version/@major")[0])
                minor = int(elem.xpath("meta/version/@minor")[0])
                LOGGER.debug("Database version is %d.%d" % (major, minor))
                if major != Database.XML_VERSION[0]:
                    raise DatabaseException("Unknown database version %d.%d" % (major, minor))
                    # do migration is possible
            else:
                LOGGER.warning("Unknown database version %d.%d" % (major, minor))

            LOGGER.debug("Parsing accounts...")
            Account.parseFromXml(elem.xpath("accounts")[0], db)

            LOGGER.debug("Parsing transactions...")
            Transaction.parseFromXml(elem.xpath("transactions")[0], db)

            LOGGER.debug("Parsed database with %d accounts and %d transactions", db.nofAccounts(), db.nofTransactions())
        except:
            LOGGER.exception("Failed to parse database")
            raise
        finally:
            db._parsing = False
        return db

    @property
    def parsing(self):
        """Return true when database is in process of parsing from xml."""
        return self._parsing

    def toXml(self):
        root = etree.Element("database")
        metaElem = etree.SubElement(root, "meta")
        versionElem = etree.SubElement(metaElem, "version")
        versionElem.set("major", str(Database.XML_VERSION[0]))
        versionElem.set("minor", str(Database.XML_VERSION[1]))
        savedElem = etree.SubElement(metaElem, "saved")
        savedElem.set("datetime", str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        accElem = etree.SubElement(root, "accounts")
        for acc in self._childAccounts:
            acc.toXml(accElem)

        trnElem = etree.SubElement(root, "transactions")
        for t in self._transactions:
            t.toXml(trnElem)

        return root

    @staticmethod
    def load(path):
        """Return database instance loaded from given file path."""
        f = None
        if zipfile.is_zipfile(path):
            zf = zipfile.ZipFile(path, mode="r")
            for zi in zf.infolist():
                if zi.filename == Database.CURRENT_DB_NAME:
                    f = zf.open(zi)
                    break
        else:
            f = open(path, "rb")
        return Database.parseFromXml(etree.parse(f).getroot())

    def _saveAppendToZip(self, data, path):
        """Append new entry to given zip file, keeping most recent entries too."""
        dtNow = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backupDb = "%s.accdb" % dtNow
        with open(path, "rb") as f:
            inMemZip = BytesIO(f.read())
        outMemZip = BytesIO()
        with zipfile.ZipFile(inMemZip, mode="r") as tmpZip, \
                zipfile.ZipFile(outMemZip, mode="w", compression=zipfile.ZIP_DEFLATED) as newZip:
            recentZipInfos = tmpZip.infolist()
            recentZipInfos.sort(key=lambda info: info.date_time, reverse=True)
            for zi in recentZipInfos[:10]:  # only keep the most recent backups in zip
                zff = tmpZip.open(zi)
                if zi.filename == Database.CURRENT_DB_NAME:
                    zi.filename = backupDb
                    zi.orig_filename = backupDb
                LOGGER.debug("Keeping backup %s" % zi.filename)
                newZip.writestr(zi, zff.read())
            LOGGER.debug("Adding %s" % Database.CURRENT_DB_NAME)
            newZip.writestr(Database.CURRENT_DB_NAME, data)
        with open(path, "wb+") as f:
            f.write(outMemZip.getvalue())

    def _saveToZip(self, data, path):
        """Save data to given zip file"""
        with zipfile.ZipFile(path, mode="w", compression=zipfile.ZIP_DEFLATED) as newZip:
            newZip.writestr(Database.CURRENT_DB_NAME, data)

    def _saveToPlainFile(self, data, path):
        """Save to file, moving previous content to new file postfixed with date string"""
        dtNow = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup, ext = os.path.splitext(path)
        backup += "_" + dtNow
        shutil.copy(path, backup + ext)
        with open(path, "wb+") as f:
            f.write(data)

    def save(self, path, backup=True):
        """Save database to given file path."""
        xml = etree.tostring(self.toXml(),
                             encoding="utf-8",
                             xml_declaration=True,
                             pretty_print=True)
        if backup and zipfile.is_zipfile(path):
            self._saveAppendToZip(xml, path)
        elif backup and os.path.isfile(path):
            self.__saveToPlainFile(xml, path)
        else:
            self._saveToZip(xml, path)


class FilterGreaterOrEqualDate(Filter):
    """Accept date that is equal or greater than given date"""

    def __init__(self, fromDate):
        super().__init__()
        self._fromDate = date_from_value(fromDate)

    def __repr__(self):
        return "FilterGreaterOrEqualDate(fromDate={!r})".format(self._fromDate)

    def _accepted(self, obj):
        if isinstance(obj, Item):
            return obj.transaction.date >= self._fromDate
        if isinstance(obj, Transaction):
            return obj.date >= self._fromDate
        raise TypeError("Don't know how to handle type " + type(obj))


class FilterLessOrEqualDate(Filter):
    """Accept date that is equal or greater than given date"""

    def __init__(self, tillDate):
        super().__init__()
        self._tillDate = date_from_value(tillDate)

    def __repr__(self):
        return "FilterLessOrEqualDate(tillDate={!r})".format(self._tillDate)

    def _accepted(self, obj):
        if isinstance(obj, Item):
            return obj.transaction.date <= self._tillDate
        if isinstance(obj, Transaction):
            return obj.date <= self._tillDate
        raise TypeError("Don't know how to handle type " + type(obj))


class FilterDateRange(Filter):
    """Accept date that is between (including) from and till date"""

    def __init__(self, fromDate, tillDate):
        super().__init__()
        self._fromDate = date_from_value(fromDate)
        self._tillDate = date_from_value(tillDate)
        if self._fromDate > self._tillDate:
            self._fromDate, self._tillDate = self._tillDate, self._fromDate

    def __repr__(self):
        return "FilterDateRange(fromDate={!r},tillDate={!r})".format(self._fromDate, self._tillDate)

    def _accepted(self, obj):
        if isinstance(obj, Item):
            return obj.transaction.date >= self._fromDate and obj.transaction.date <= self._tillDate
        if isinstance(obj, Transaction):
            return obj.date >= self._fromDate and obj.date <= self._tillDate
        raise TypeError("Don't know how to handle type " + type(obj))


class FilterAccountTypes(Filter):
    """Accept given account types"""

    def __init__(self, *types):
        super().__init__()
        self._types = tuple([type for type in types if type in Account.ALL_TYPES])

    def _accepted(self, obj):
        if isinstance(obj, Item):
            return obj.account.typeDerived in self._types
        elif isinstance(obj, Transaction):
            return obj.hasItems(self)
        else:
            raise TypeError("Don't know how to handle type " + type(obj))


class FilterAccounts(Filter):
    """Accept given accounts"""

    def __init__(self, *accounts):
        super().__init__()
        self._accounts = tuple(filter(lambda acc: isinstance(acc, Account), accounts))

    def _accepted(self, obj):
        if isinstance(obj, Item):
            return obj.account in self._accounts
        elif isinstance(obj, Transaction):
            if obj.hasItems(self):
                return True
            return False
        else:
            raise TypeError("Don't know how to handle type " + type(obj))


class FilterAccountsAndChildren(Filter):
    """Accept given accounts and their nested account(s)"""

    def __init__(self, *accounts):
        super().__init__()
        self._accounts = tuple(filter(lambda acc: isinstance(acc, Account), accounts))

    def _accepted(self, obj):
        if isinstance(obj, Item):
            for acc in self._accounts:
                if acc.isSelfOrHasChildAccount(obj.account):
                    return True
            return False
        elif isinstance(obj, Transaction):
            if obj.hasItems(self):
                return True
            return False
        else:
            raise TypeError("Don't know how to handle type " + type(obj))


class FilterNotAccountsAndChildren(Filter):
    """Accept all but given accounts and their nested account(s)"""

    def __init__(self, *accounts):
        super().__init__()
        self._accounts = tuple(filter(lambda acc: isinstance(acc, Account), accounts))

    def _accepted(self, obj):
        if isinstance(obj, Item):
            for acc in self._accounts:
                if acc.isSelfOrHasChildAccount(obj.account):
                    return False
            return True
        elif isinstance(obj, Transaction):
            if obj.hasItems(self):
                return False
            return True
        else:
            raise TypeError("Don't know how to handle type " + type(obj))


class FilterEqualValue(Filter):
    """Accept value that is equal to given value"""

    def __init__(self, value):
        super().__init__()
        self._value = value

    def __repr__(self):
        return "FilterEqualValue(value={!r})".format(self._value)

    def _accepted(self, obj):
        if isinstance(obj, Item):
            if self._value == obj.value:
                return True
            if self._accepted(obj.transaction):
                return True
            return False
        if isinstance(obj, Transaction):
            for item in obj:
                if self._value == item.value:
                    return True
            return False
        raise TypeError("Don't know how to handle type " + type(obj))


class FilterRegexpDescr(Filter):
    "Accept description that matches given regular expression object"

    def __init__(self, regexp):
        super().__init__()
        self._re = regexp

    def __repr__(self):
        return "FilterRegexpDescr(regexp={!r})".format(self._re)

    def _accepted(self, obj):
        txts = []
        if isinstance(obj, Item):
            txts += obj.descr
            txts += [obj.transaction.descr]
            txts += [item.descr for item in obj.transaction if item is not obj]
        elif isinstance(obj, Transaction):
            txts += [obj.descr]
            txts += [item.descr for item in obj]
        else:
            raise TypeError("Don't know how to handle type " + type(obj))
        for t in txts:
            if self._re.search(t):
                return True
        return False
