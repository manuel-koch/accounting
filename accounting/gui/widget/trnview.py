# -*- coding: utf-8 -*-
'''
View of account's transactions

@author: Manuel Koch
'''
import datetime
import re
import logging

from PyQt5 import QtGui, QtWidgets, QtCore

from accounting.gui.widget.trntable import AccountTable
from accounting.core.value import to_decimal
from accounting.core.filter import Filter, CombinedFilter
from accounting.core.core import FilterDateRange, FilterGreaterOrEqualDate, FilterEqualValue, FilterRegexpDescr
from accounting.gui.widget.impview import TransactionImportView
from accounting.core import dateutils

LOGGER = logging.getLogger(__name__)


class DateRange(QtWidgets.QWidget):
    dateClicked = QtCore.pyqtSignal(datetime.date)

    WIDTH = 55

    def __init__(self):
        "Construct widget to draw a date scale"
        super().__init__()
        self.setMinimumWidth(DateRange.WIDTH)
        self._from = None
        self._till = None
        self._font = QtGui.QFont()
        self._font.setPointSize(10)
        self._labelHeight = 0

    def mousePressEvent(self, mouseEvent):
        super().mousePressEvent(mouseEvent)
        f = float(mouseEvent.y()) / self.height()
        if f <= 0.05:
            f = 0
        elif f >= 0.95:
            f = 1.0
        secs = (self._till - self._from).total_seconds()
        d = self._from + datetime.timedelta(seconds=secs * f)
        self.dateClicked.emit(d)

    def paintEvent(self, evt):
        if not self._from or not self._till:
            return

        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setFont(self._font)
        painter.setRenderHint(QtGui.QPainter.Antialiasing);

        dt = self._till - self._from
        step = datetime.timedelta(days=1)
        d = self._from
        flags = QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter
        label_data = []
        last_t = None
        while d <= self._till:
            if dt:
                f = (d - self._from).total_seconds() / dt.total_seconds()
            else:
                f = 0
            t = d.strftime("%b %Y")
            if t != last_t:
                h = painter.boundingRect(0, 0, self.width(), 20, QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop, t).height()
                y = int(self.height() * f)
                if y - h / 2 < 0:
                    y = h / 2
                elif y + h / 2 > self.height():
                    y = self.height() - h / 2
                last_t = t
                label_data.append((t, y, h))
            d += step

        print("lower half")
        i = 1
        while i < len(label_data) // 2:
            prev_y = label_data[i - 1][1]
            prev_h = label_data[i - 1][2]
            y = label_data[i][1]
            overlap = (prev_y + prev_h) > y
            print(i, y, prev_y, prev_h, overlap)
            if overlap:
                print("drop", i)
                label_data.pop(i)
            else:
                i += 1

        print("upper half")
        i = -2
        while i > (-len(label_data) // 2):
            prev_y = label_data[i + 1][1]
            prev_h = label_data[i + 1][2]
            y = label_data[i][1]
            overlap = (prev_y - prev_h) < y
            print(i, y, prev_y, prev_h, overlap)
            if overlap:
                print("drop", i)
                label_data.pop(i)
            else:
                i -= 1

        for t, y, h in label_data:
            painter.drawText(0, y - h / 2, self.width(), h, flags, t)

        painter.end()

    def setDateRange(self, fromDate, tillDate):
        self._from = fromDate if fromDate is not None and fromDate < datetime.date.max else None
        self._till = tillDate if tillDate is not None and tillDate > datetime.date.min else None
        self.update()


class TransactionFilterWidget(QtWidgets.QWidget):
    filterChanged = QtCore.pyqtSignal(object)

    DATE_RANGE_ALL = "all"
    DATE_RANGE_CURR_MONTH = "current month"
    DATE_RANGE_LAST_90_DAYS = "last 90 days"
    DATE_RANGE_CURR_YEAR = "current year"

    def __init__(self):
        "Construct view to edit account's transaction."
        super().__init__()

        self._delayTimer = QtCore.QTimer()
        self._delayTimer.setSingleShot(True)
        self._delayTimer.timeout.connect(self._filterChanged)

        form = QtWidgets.QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(4)
        self._rangeCombo = QtWidgets.QComboBox()
        self._rangeCombo.addItems([self.DATE_RANGE_ALL,
                                   self.DATE_RANGE_CURR_MONTH,
                                   self.DATE_RANGE_LAST_90_DAYS,
                                   self.DATE_RANGE_CURR_YEAR])
        self._rangeCombo.setCurrentText(self.DATE_RANGE_LAST_90_DAYS)
        self._rangeCombo.setEditable(False)
        self._rangeCombo.currentTextChanged.connect(self._filterChanged)
        self._descrText = QtWidgets.QLineEdit()
        self._descrText.setMinimumWidth(300)
        self._descrText.textChanged.connect(lambda: self._delayTimer.start(300))
        self._valueText = QtWidgets.QLineEdit()
        self._valueText.setMinimumWidth(300)
        self._valueText.textChanged.connect(lambda: self._delayTimer.start(300))
        form.addRow(QtWidgets.QLabel("Date range"), self._rangeCombo)
        form.addRow(QtWidgets.QLabel("Description:"), self._descrText)
        form.addRow(QtWidgets.QLabel("Value:"), self._valueText)
        self.setLayout(form)

    def _filterChanged(self):
        self.filterChanged.emit(self.getFilter())

    def getFilter(self):
        try:
            value = str(self._valueText.text()).strip()
            if value:
                value = to_decimal(value)
            else:
                value = None
        except:
            value = None
        descr = str(self._descrText.text()).strip()

        today = datetime.date.today()
        filter_ = CombinedFilter()

        if value is not None:
            filter_ = filter_ & FilterEqualValue(value)

        if descr:
            regexp = re.compile(re.escape(descr), re.IGNORECASE)
            filter_ = filter_ & FilterRegexpDescr(regexp)

        if self._rangeCombo.currentText() == self.DATE_RANGE_CURR_MONTH:
            start_ts = dateutils.startofmonth(today)
            filter_ = filter_ & FilterGreaterOrEqualDate(start_ts)
        elif self._rangeCombo.currentText() == self.DATE_RANGE_LAST_90_DAYS:
            start_ts = today - datetime.timedelta(days=90)
            filter_ = filter_ & FilterGreaterOrEqualDate(start_ts)
        elif self._rangeCombo.currentText() == self.DATE_RANGE_CURR_YEAR:
            start_ts = dateutils.startofyear(today)
            filter_ = filter_ & FilterGreaterOrEqualDate(start_ts)

        return filter_

    def show(self):
        super().show()
        self._descrText.setFocus()


class AccountTransactionView(QtWidgets.QWidget):
    # Whether model has been altered and needs saving
    dirty = QtCore.pyqtSignal(bool)

    def __init__(self):
        "Construct view to edit account's transaction."
        super().__init__()
        hbox = QtWidgets.QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)

        vbox = QtWidgets.QVBoxLayout()
        vbox.setSpacing(4)
        vbox.setContentsMargins(0, 0, 0, 0)
        hbox.addLayout(vbox)

        self._importView = TransactionImportView()
        self._importView.importDone.connect(self.stopImport)
        self._importView.importEntrySelected.connect(self._importEntrySelected)
        self._importView.importEntryDeselected.connect(self._importEntryDeselected)
        self._importView.importEntryAsTransaction.connect(self._importEntryAsTransaction)
        self._importView.importEntryAsItem.connect(self._importEntryAsItem)
        self._importView.importEntryToItem.connect(self._importEntryToItem)
        self._importView.hide()
        vbox.addWidget(self._importView)

        self._filterWidget = TransactionFilterWidget()
        vbox.addWidget(self._filterWidget)

        tblhbox = QtWidgets.QHBoxLayout()
        tblhbox.setContentsMargins(0, 0, 0, 0)
        tblhbox.setSpacing(2)
        self._dateRange = DateRange()
        self._dateRange.dateClicked.connect(self._selectNearDate)
        tblhbox.addWidget(self._dateRange)
        self._acctbl = AccountTable()
        self._acctbl.dirty.connect(self.dirty)
        self._acctbl.dateRangeChanged.connect(self._dateRange.setDateRange)
        self._acctbl.searching.connect(self.toggleFiltering)
        tblhbox.addWidget(self._acctbl, 1)
        vbox.addLayout(tblhbox, 1)

        self._filterWidget.filterChanged.connect(self._acctbl.applyFilter)

        self.setLayout(hbox)

    def startImport(self):
        "Trigger start of import of transaction data for current account"
        self._filterWidget.hide()
        self._importView.startImport()
        self._acctbl.applyFilter(None)

    def stopImport(self):
        "Handle end of import"
        self._importView.hide()
        self._filterWidget.show()
        self._acctbl.applyFilter(None)
        self._acctbl.applyFilter(self._filterWidget.getFilter())

    def toggleFiltering(self):
        "Toggle filtering table entries by customizable filter constraints"
        if self._filterWidget.isHidden():
            self._filterWidget.show()
            self._recentRangeCombo.hide()
        else:
            self._filterWidget.hide()
            self._recentRangeCombo.show()

    def setAccount(self, acc):
        "Set account to be displayed in view"
        self._acctbl.setAccount(acc)
        self._acctbl.applyFilter(self._filterWidget.getFilter())

    def getAccount(self):
        "Get account that is currently displayed in view"
        return self._acctbl.getAccount()

    def isDirty(self):
        "Return true when model has been altered and needs saving."
        return self._acctbl.isDirty()

    def setDirty(self, isDirty):
        "Set whether model has been altered and needs saving."
        return self._acctbl.setDirty(isDirty)

    def refreshFromModel(self):
        "Refresh account view from model"
        self._acctbl.refreshFromModel()

    def _selectNearDate(self, date):
        self._acctbl.selectTransaction(date=date)

    def _importEntrySelected(self, entry):
        delta = datetime.timedelta(days=14)
        dateRangeFilter = FilterDateRange(entry.date - delta, entry.date + delta)
        valueFilter = FilterEqualValue(entry.value)
        if self._importView.filterByDateOnly():
            entryFilter = dateRangeFilter
        else:
            entryFilter = dateRangeFilter & valueFilter
        if self._importView.filterOnSelection():
            self._acctbl.applyFilter(entryFilter)
        else:
            self._acctbl.applyFilter(None)
        self._acctbl.selectTransaction(entryFilter, entry.date)

    def _importEntryDeselected(self):
        self._acctbl.applyFilter(None)

    def _importEntryAsTransaction(self, entry):
        self._acctbl.addTransaction(date=entry.date, descr=entry.descr,
                                    value=entry.value, confirmed=entry.confirmed)

    def _importEntryAsItem(self, entry):
        self._acctbl.addItem(descr=entry.descr,
                             value=entry.value, confirmed=entry.confirmed)

    def _importEntryToItem(self, entry):
        self._acctbl.changeTransactionItem(date=entry.date, descr=entry.descr,
                                           value=entry.value, confirmed=entry.confirmed)
