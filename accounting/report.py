# -*- coding: utf-8 -*-
'''
Created on 28.04.2013

@author: manuel
'''
import os
import itertools
from functools import total_ordering

import jinja2
from decimal import Decimal

from accounting.core.core import Database, Account, Item, FilterAccountTypes
from accounting.core.core import FilterGreaterOrEqualDate, FilterLessOrEqualDate
from accounting.core.core import FilterAccounts, FilterAccountsAndChildren, FilterNotAccountsAndChildren
from accounting.core.dateutils import rangeDateFromTillByInterval, INTERVAL_MONTHLY
from accounting.core.dateutils import getIntervalDescr, getIntervalSteps


class ItemGrouping(object):
    """Base class to group multiple items by criteria."""

    def __init__(self):
        self._groups = {}
        self._items = []

    def _getGroupKey(self, item):
        """Get a group key for given report item. Derived classes must overwrite this method."""
        raise NotImplemented()

    def __contains__(self, instance):
        """Return true when instance exists in group."""
        if isinstance(instance, Item):
            return instance in self._items
        return False

    def __iadd__(self, other):
        """Add instance to grouping."""
        if isinstance(other, Item):
            if not other in self:
                key = self._getGroupKey(other)
                if not key in self._groups:
                    self._groups[key] = []
                self._groups[key].append(other)
                self._items.append(other)
        elif isinstance(other, Report):
            for item in other.items:
                self += item
        else:
            raise TypeError()
        return self

    def __isub__(self, other):
        """Remove instance from grouping."""
        if isinstance(other, Item):
            if other in self:
                key = self._getGroupKey(other)
                self._groups[key].remove(other)
                self._items.remove(other)
        elif isinstance(other, Report):
            for item in other.items:
                self -= item
        else:
            raise TypeError()
        return self

    def clear(self):
        """Clear grouping."""
        self._groups = {}
        self._items = []

    def groups(self):
        """Return list of groupings."""
        return self._groups.keys()

    def groupItems(self, key, filter_=None):
        """Return items for selecting grouping key that match given filter"""
        if filter_ is None:
            return iter(self._groups[key])
        else:
            return itertools.filterfalse(filter_.rejected, self._groups[key])


@total_ordering
class DateRangeKey(object):

    def __init__(self, fromDate, tillDate, interval):
        self._interval = interval
        self._fromDate, self._tillDate = rangeDateFromTillByInterval(fromDate, tillDate, self._interval)

    def __repr__(self):
        return "%s...%s" % (self._fromDate, self._tillDate)

    def __str__(self):
        return getIntervalDescr(self._fromDate, self._tillDate, self._interval)

    def __eq__(self, other):
        if not isinstance(other, DateRangeKey):
            return NotImplemented
        return self._fromDate == other._fromDate and self._tillDate == other._tillDate

    def __lt__(self, other):
        if not isinstance(other, DateRangeKey):
            return NotImplemented
        return self._fromDate < other._fromDate

    def __hash__(self):
        return hash((self._fromDate, self._tillDate))


class ItemGroupingByDateRange(ItemGrouping):
    """Group multiple report items by date range."""

    def __init__(self, fromDate, tillDate, interval):
        super().__init__()
        self._fromDate = fromDate
        self._tillDate = tillDate
        self._interval = interval

        # make sure we have a list for every date range
        for i in getIntervalSteps(self._fromDate, self._tillDate, self._interval):
            key = DateRangeKey(i, i, self._interval)
            self._groups[key] = []

    def _getGroupKey(self, item):
        """Get a group key for given item."""
        d = item.date
        return DateRangeKey(d, d, self._interval)

    def groups(self):
        """Return list of groupings."""
        groups = list(super().groups())
        groups.sort()
        return groups


class ReportDatasetValue(object):
    """A value within a group"""

    def __init__(self, label, value, items):
        """Construct a group"""
        self._label = label
        self._value = value
        self._items = items
        self._grp = None

    def __repr__(self):
        return "%s %s" % (self._label, self._value)

    def __str__(self):
        return "%s %s" % (self._label, self._value)

    @property
    def rgb(self):
        return "rgb(%d,%d,%d)" % self._rgb

    @property
    def rgbaFill(self):
        return "rgba(%d,%d,%d,0.5)" % self._rgb

    @property
    def rgbaStroke(self):
        return "rgba(%d,%d,%d,1.0)" % self._rgb

    @property
    def label(self):
        return self._label

    @property
    def value(self):
        return self._value

    @property
    def items(self):
        return self._items

    @property
    def percent(self):
        if self._grp and self._grp.sum:
            pct = float(self._value * 100 / self._grp.sum)
        else:
            pct = 100
        return pct


class ReportDatasetGroup(object):
    """A group within a dataset"""

    def __init__(self, label):
        """Construct a group"""
        self._label = label
        self._values = []

    def __repr__(self):
        return str(self._label)

    def __str__(self):
        return str(self._label)

    def __iadd__(self, other):
        """Add instance to group."""
        if isinstance(other, ReportDatasetValue):
            if not other in self._values:
                self._values += [other]
                other._grp = self
        else:
            raise TypeError("Dont know how to handle %s" % type(other))
        return self

    def __len__(self):
        return len(self._values)

    def __getitem__(self, key):
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def sorted(self, maxNof=0):
        """Return sorted list of values in descending order. Only return max number of values if requested."""
        vals = [v for v in self._values if v.value]
        vals.sort(key=lambda v: v.value, reverse=True)
        if maxNof and len(vals) > maxNof:
            vals, other = vals[:maxNof - 1], vals[maxNof + 1:]
            sumOther = sum([v.value for v in other])
            if sumOther:
                vals += [ReportDatasetValue("...", sumOther, [])]
        return vals

    @property
    def sum(self):
        """Return sum of all values in group"""
        return sum(map(lambda v: v.value, self._values))

    @property
    def label(self):
        """Return group's label"""
        return self._label

    @property
    def series(self):
        """Return list of series labels of group"""
        return [v.label for v in self._values]


class ReportDataset(object):
    """A dataset of a report, grouped items of account.
    Dataset contains multiple groups.
    Every group has multiple values."""

    def __init__(self):
        """Construct a dataset"""
        self._groups = []

    def __iadd__(self, other):
        """Add instance to dataset."""
        if isinstance(other, ReportDatasetGroup):
            if not other in self._groups:
                self._groups += [other]
        elif isinstance(other, ReportDatasetValue):
            g = self._groups[-1]
            g += other
        else:
            raise TypeError("Dont know how to handle %s" % type(other))
        return self

    def __len__(self):
        return len(self._groups)

    def __getitem__(self, key):
        return self._groups[key]

    def __iter__(self):
        return iter(self._groups)

    @property
    def series(self):
        """Return labels of series of dataset"""
        if self._groups:
            return self._groups[0].series
        else:
            return []

    def dump(self):
        for dtgrp in self._groups:
            print(dtgrp)
            for dtval in dtgrp:
                print(dtval)


class Report(object):
    """A report from database."""

    RGB_COLORS = ((220, 220, 220),
                  (151, 187, 205),
                  (200, 180, 180),
                  (250, 180, 180))

    def __init__(self, db, fromDate, tillDate):
        if not isinstance(db, Database):
            raise TypeError("Expected Database instance")
        self._db = db
        self._accounts = []
        self._datasets = {}
        self.setRange(fromDate, tillDate)

    def __iadd__(self, other):
        """Add instance to report."""
        if isinstance(other, Account):
            if not other in self._accounts:
                self._accounts.append(other)
        else:
            raise TypeError("Dont know how to handle %s" % type(other))
        return self

    def __isub__(self, other):
        """Remove instance from report."""
        if isinstance(other, Account):
            if other in self._accounts:
                self._account.remove(other)
        else:
            raise TypeError("Dont know how to handle %s" % type(other))
        return self

    @property
    def fromDate(self):
        return self._fromDate

    @property
    def tillDate(self):
        return self._tillDate

    def setRange(self, fromDate, tillDate):
        """Set date range of report."""
        self._fromDate = fromDate
        self._tillDate = tillDate
        self._items = None
        self._datasets = {}

    @property
    def accounts(self):
        """Returns iterator for accounts of this report."""
        return iter(self._accounts)

    @property
    def items(self):
        """Get iterator for items generated by this report."""
        if self._items is not None:
            return self._items
        fromFilter = FilterGreaterOrEqualDate(self._fromDate)
        tillFilter = FilterLessOrEqualDate(self._tillDate)
        dateFilter = fromFilter & tillFilter
        accFilter = FilterAccountsAndChildren(*self._accounts)
        self._items = list(self._db.filterItems(accFilter & dateFilter))
        return iter(self._items)

    def datasetMonthly(self):
        """Return dataset for items grouped by account and sum of values per monthly interval"""
        if "monthly" in self._datasets:
            return self._datasets["monthly"]
        dataset = ReportDataset()
        grp = ItemGroupingByDateRange(self._fromDate, self._tillDate, INTERVAL_MONTHLY)
        grp += self
        for label in grp.groups():
            dataset += ReportDatasetGroup(label)
            for acc in self._accounts:
                accInclFilter = FilterAccountsAndChildren(acc)
                accExclFilter = FilterNotAccountsAndChildren(*filter(lambda a: acc.hasChildAccount(a), self._accounts))
                items = list(grp.groupItems(label, accInclFilter & accExclFilter))
                accsum = sum(items)
                items.sort(key=lambda x: x.date)
                dataset += ReportDatasetValue(acc.fullname, accsum, items)
        self._datasets["monthly"] = dataset
        return self._datasets["monthly"]

    def datasetMonthlyExpanded(self):
        """Return dataset for items grouped by expanded account ( resolving child accounts
        from current selected accounts ) and sum of values per monthly interval"""
        if "monthlyExpanded" in self._datasets:
            return self._datasets["monthlyExpanded"]
        dataset = ReportDataset()
        grp = ItemGroupingByDateRange(self._fromDate, self._tillDate, INTERVAL_MONTHLY)
        grp += self
        allAccounts = []
        for acc in self._accounts:
            if acc not in allAccounts:
                allAccounts += [acc]
                for subacc in acc.getChildAccounts(True):
                    if subacc not in allAccounts:
                        allAccounts += [subacc]
        for label in grp.groups():
            dataset += ReportDatasetGroup(label)
            for acc in allAccounts:
                accFilter = FilterAccounts(acc)
                items = list(grp.groupItems(label, accFilter))
                accsum = sum(items)
                items.sort()
                dataset += ReportDatasetValue(acc.fullname, accsum, items)
        self._datasets["monthlyExpanded"] = dataset
        return self._datasets["monthlyExpanded"]

    def datasetMonthlyTypes(self):
        """Return dataset for items grouped by asset type and sum of values per monthly interval"""
        if "monthlyTypes" in self._datasets:
            return self._datasets["monthly"]
        dataset = ReportDataset()
        grp = ItemGroupingByDateRange(self._fromDate, self._tillDate, INTERVAL_MONTHLY)
        grp += self
        for label in grp.groups():
            balance = Decimal()
            dataset += ReportDatasetGroup(label)
            for type in (Account.TYPE_ASSET, Account.TYPE_LIABILITY, Account.TYPE_PROFIT, Account.TYPE_EXPENSE):
                typeFilter = FilterAccountTypes(type)
                items = list(grp.groupItems(label, typeFilter))
                typesum = sum([i.valueDerived for i in items])
                if type in (Account.TYPE_PROFIT,Account.TYPE_EXPENSE):
                    balance += typesum
                items.sort(key=lambda x: x.date)
                dataset += ReportDatasetValue(Account.ALL_TYPES[type], typesum, items)
            dataset += ReportDatasetValue("Balance", balance, [])
        self._datasets["monthlyTypes"] = dataset
        return self._datasets["monthlyTypes"]


class ReportTemplate(object):
    """Represents a text templates that can be feed by report output to generate e.g. HTML."""

    def __init__(self, basepath, name):
        """Create report template of given name using selected search path."""
        if not os.path.isdir(basepath):
            raise IOError("Dir not found: " + basepath)
        self._basePath = os.path.abspath(basepath)
        self._env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=self._basePath),
                                       extensions=['jinja2.ext.loopcontrols'])
        self._name = name
        self._nextId = 1

    @property
    def name(self):
        return self._name

    @property
    def path(self):
        return os.path.join(self._basePath, self._name)

    @property
    def basepath(self):
        return self._basePath

    def raw(self):
        """Return raw text of the template."""
        tmpl = self._env.get_template(self._name)
        return open(tmpl.filename, "rb").read()

    def _newId(self):
        """Create a new identifier"""
        currId = self._nextId
        self._nextId += 1
        return currId

    def render(self, report):
        """Render template with data generated by given report."""
        if not isinstance(report, Report):
            raise TypeError("Expected Report instance")
        ctxt = {}
        ctxt["report"] = report
        ctxt["newid"] = self._newId
        tmpl = self._env.get_template(self._name)
        return tmpl.render(**ctxt)
