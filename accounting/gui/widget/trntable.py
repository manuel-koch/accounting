# -*- coding: utf-8 -*-
'''
Table view of account's transactions

@author: Manuel Koch
'''

import datetime
import logging
from PyQt5 import QtGui, QtWidgets, QtCore

from accounting.gui.models import AccountTransactionsModel, CustomTransactionFilter

from accounting.gui.widget.delegates import DateDelegate
from accounting.gui.widget.delegates import DescriptionDelegate
from accounting.gui.widget.delegates import AccountDelegate
from accounting.gui.widget.delegates import ValueDelegate

LOGGER = logging.getLogger(__name__)


class AccountTable(QtWidgets.QTableView):
    # Whether model has been altered and needs saving
    dirty = QtCore.pyqtSignal(bool)

    MIN_COL_WIDTHS = (  # column using minimum width
        AccountTransactionsModel.COL_DATE,
        AccountTransactionsModel.COL_CONF,
        AccountTransactionsModel.COL_ASSET,
        AccountTransactionsModel.COL_DEBIT,
        AccountTransactionsModel.COL_ACCU,
    )

    SPREAD_COL_WIDTHS = (  # column spreading remaining space by factor
        (AccountTransactionsModel.COL_DESCR, 2),
        (AccountTransactionsModel.COL_ACC, 1),
    )

    # signal change of first/last transaction date
    dateRangeChanged = QtCore.pyqtSignal(datetime.date, datetime.date)

    # signal that user requested searching in table
    searching = QtCore.pyqtSignal()

    def __init__(self):
        """Construct account's transactions table view."""
        super().__init__()
        self._acc = None
        self._model = None
        self._editOnInsert = True
        self._adjustColumnsOnInsert = False
        self.setMinimumWidth(200)
        self.setEditTriggers(self.EditKeyPressed | self.AnyKeyPressed | self.DoubleClicked)
        self.setItemDelegateForColumn(AccountTransactionsModel.COL_DATE, DateDelegate(self))
        self.setItemDelegateForColumn(AccountTransactionsModel.COL_DESCR, DescriptionDelegate(self))
        self.setItemDelegateForColumn(AccountTransactionsModel.COL_ACC, AccountDelegate(self))
        self.setItemDelegateForColumn(AccountTransactionsModel.COL_ASSET, ValueDelegate(self))
        self.setItemDelegateForColumn(AccountTransactionsModel.COL_DEBIT, ValueDelegate(self))
        self.setItemDelegateForColumn(AccountTransactionsModel.COL_ACCU, ValueDelegate(self))
        self.verticalHeader().setDefaultSectionSize(20)
        self.verticalHeader().setFixedWidth(38)
        font = self.verticalHeader().font()
        font.setPointSize(10);
        self.verticalHeader().setFont(font)
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.horizontalHeader().setResizeContentsPrecision(250)

    def resizeEvent(self, resizeEvent):
        super().resizeEvent(resizeEvent)
        self.adjustColumnWidths()

    def adjustColumnWidths(self):
        """Adjust width of all columns to use all available space."""
        hw = self.horizontalHeader().size().width()
        for c in AccountTable.MIN_COL_WIDTHS:
            cw = self.sizeHintForColumn(c)
            hw -= cw
            self.setColumnWidth(c, cw)
        fSum = sum([w[1] for w in AccountTable.SPREAD_COL_WIDTHS])
        for c, f in AccountTable.SPREAD_COL_WIDTHS:
            cw = hw * f / fSum
            self.setColumnWidth(c, cw)

    def keyPressEvent(self, keyEvent):
        """Handle key press event."""
        isCtrl = QtWidgets.QApplication.keyboardModifiers() & QtCore.Qt.ControlModifier
        if keyEvent.key() == QtCore.Qt.Key_Plus:
            self.model().insertRow(self.currentIndex().row())
        elif keyEvent.key() == QtCore.Qt.Key_Minus:
            self.model().removeRow(self.currentIndex().row())
        elif isCtrl and keyEvent.key() == QtCore.Qt.Key_B:
            self.model().balanceTransaction(self.currentIndex())
        elif isCtrl and keyEvent.key() == QtCore.Qt.Key_F:
            self.searching.emit()
        else:
            super().keyPressEvent(keyEvent)

    def setAccount(self, acc):
        """Set account to be displayed in table"""
        self._acc = acc
        self._model = CustomTransactionFilter()
        self._model.setSourceModel(AccountTransactionsModel(acc))
        self._model.setDynamicSortFilter(True)
        self.setModel(self._model)
        self._model.dirty.connect(self.dirty)
        self._model.rowsInserted.connect(self._onRowsInserted)
        self._model.rowsMoved.connect(self._onRowsMoved)
        self._model.dateRangeChanged.connect(self.dateRangeChanged)
        fromDate, tillDate = self._model.getDateRange()
        if fromDate and tillDate:
            self.dateRangeChanged.emit(fromDate, tillDate)

    def getDateRange(self):
        """Returns tuple of first and last date of transactions for current account"""
        return self._model.getDateRange()

    def _onRowsInserted(self, idx, firstRow, lastRow):
        """React on insertion of new rows."""
        if self._adjustColumnsOnInsert:
            self.adjustColumnWidths()
            self._adjustColumnsOnInsert = False

        self.selectRow(firstRow)
        idx = self.model().index(firstRow, AccountTransactionsModel.COL_DESCR)
        rowType = self.model().data(idx, AccountTransactionsModel.RowTypeRole)
        if rowType == AccountTransactionsModel.RowTypeTransaction:
            self.scrollTo(idx, AccountTable.PositionAtCenter)
        if self._editOnInsert:
            self.edit(idx)

    def _onRowsMoved(self, srcIdx, firstRow, lastRow, dstIdx, destRow):
        """React on moved rows."""
        idx = self.model().index(destRow, AccountTransactionsModel.COL_DESCR)
        rowType = self.model().data(idx, AccountTransactionsModel.RowTypeRole)
        if rowType == AccountTransactionsModel.RowTypeTransaction:
            self.scrollTo(idx, AccountTable.PositionAtCenter)

    def getAccount(self):
        """Return account currently displayed in table."""
        return self._acc

    def isDirty(self):
        """Return true when model has been altered and needs saving."""
        return self._model.isDirty()

    def setDirty(self, isDirty):
        """Set whether model has been altered and needs saving."""
        return self._model.setDirty(isDirty)

    def applyFilter(self, filter_):
        """Apply given filter instance to table view"""
        self._editOnInsert = False
        self._model.filter(filter_)
        self._editOnInsert = True

        # A filter with empty result shrinks most columns, need to resize columns when content is inserted
        self._adjustColumnsOnInsert = self._model.rowCount() == 0

    def refreshFromModel(self):
        """Force refresh from model's data"""
        self._model.sourceModel().refresh()

    def selectTransaction(self, filter_=None, date=None):
        """Select a first row that is matched by given filter or near given date"""
        idx = self.model().findRow(filter_, date)
        self.setCurrentIndex(idx)
        self.scrollTo(idx, QtWidgets.QAbstractItemView.PositionAtCenter)

    def addTransaction(self, **kwargs):
        """Add new transaction using given values"""
        self.model().addTransaction(**kwargs)

    def addItem(self, **kwargs):
        """Add new item using given values"""
        self.model().addTransactionItem(self.currentIndex(), **kwargs)

    def changeTransactionItem(self, **kwargs):
        """Add new item to current transaction using given values"""
        self.model().changeTransactionItem(self.currentIndex(), **kwargs)
