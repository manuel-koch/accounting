# -*- coding: utf-8 -*-
'''
Models of data structures

@author: Manuel Koch
'''
from collections import namedtuple
import datetime
from decimal import Decimal
import logging

from PyQt5 import QtGui, QtCore

from accounting.core.core import AccountTreeItem, Account, Transaction, Item
from accounting.core.core import Filter
from accounting.core.core import FilterAccounts
from accounting.core.core import FilterAccountsAndChildren
from accounting.core.core import FilterDateRange
from accounting.core.core import FilterEqualValue

LOGGER = logging.getLogger("accounting.models")


class AccountModel(QtCore.QAbstractItemModel):
    "Represents tree model of accounts"

    # Whether model has been altered and needs saving
    dirty = QtCore.pyqtSignal(bool)

    AccountRole = QtCore.Qt.UserRole + 1

    def __init__(self, rootAccount, parent=None):
        "Construct main window."
        super().__init__(parent)
        if not isinstance(rootAccount, AccountTreeItem):
            raise TypeError()
        self._rootAccount = rootAccount
        self._dirty = False

    def setDirty(self, isDirty):
        "Set whether model has been altered and may require saving."
        self._dirty = isDirty
        self.dirty.emit(self._dirty)

    def isDirty(self):
        "Return true when model has been altered."
        return self._dirty

    """INPUTS: QModelIndex"""
    """OUTPUT: int"""

    def rowCount(self, idx):
        if not idx.isValid():
            return len(self._rootAccount.getChildAccounts())
        else:
            account = idx.internalPointer()
            return len(account.getChildAccounts())

    def insertRow(self, row, parentIdx):
        "Return True when new account has been added to parent index."
        if parentIdx.isValid():
            parentAccount = parentIdx.internalPointer()
        else:
            parentAccount = self._rootAccount
        parentRows = len(parentAccount.getChildAccounts())
        self.beginInsertRows(parentIdx, parentRows, parentRows)
        newAccount = Account("untitled%d" % parentRows)
        parentAccount += newAccount
        self.endInsertRows()
        self.setDirty(True)
        return True

    """INPUTS: QModelIndex"""
    """OUTPUT: int"""

    def columnCount(self, idx):
        return 1

    """INPUTS: QModelIndex, int"""
    """OUTPUT: QVariant, strings are cast to QString which is a QVariant"""

    def data(self, idx, role=QtCore.Qt.DisplayRole):
        if not idx.isValid():
            return None
        account = idx.internalPointer()
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            if idx.column() == 0:
                return account.name
        elif role == AccountModel.AccountRole:
            return account

    """INPUTS: QModelIndex, QVariant, int (flag)"""

    def setData(self, idx, value, role=QtCore.Qt.EditRole):
        if idx.isValid():
            if role == QtCore.Qt.EditRole:
                account = idx.internalPointer()
                ok = account.setName(value)
                if ok:
                    self.dataChanged.emit(idx, idx)
                    self.setDirty(True)
                return ok
        return False

    """INPUTS: int, Qt::Orientation, int"""
    """OUTPUT: QVariant, strings are cast to QString which is a QVariant"""

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if section == 0:
                return "Account"

    """INPUTS: QModelIndex"""
    """OUTPUT: int (flag)"""

    def flags(self, idx):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

    """INPUTS: QModelIndex"""
    """OUTPUT: QModelIndex"""
    """Should return the parent of the node with the given QModelIndex"""

    def parent(self, idx):
        account = self._getAccount(idx)
        parentAccount = account.getParentAccount()
        if parentAccount:
            return self.createIndex(parentAccount.getChildAccounts().index(account), 0, parentAccount)
        else:
            return QtCore.QModelIndex()

    """INPUTS: int, int, QModelIndex"""
    """OUTPUT: QModelIndex"""
    """Should return a QModelIndex that corresponds to the given row, column and parent node"""

    def index(self, row, column, parentIdx):
        parentAccount = self._getAccount(parentIdx)
        if parentAccount:
            childAccounts = parentAccount.getChildAccounts()
            if row < len(childAccounts):
                childAccount = childAccounts[row]
            else:
                childAccount = None
            if childAccount:
                return self.createIndex(row, column, childAccount)
        return QtCore.QModelIndex()

    """CUSTOM"""
    """INPUTS: QModelIndex"""

    def _getAccount(self, index):
        if index.isValid():
            account = index.internalPointer()
            if account:
                return account
        return self._rootAccount


class AccountTransactionsModel(QtCore.QAbstractTableModel):
    "Represents table model of transactions with items for selected account"

    # Whether model has been altered and needs saving
    dirty = QtCore.pyqtSignal(bool)

    # signal change of first/last transaction's date
    dateRangeChanged = QtCore.pyqtSignal(datetime.date, datetime.date)

    COL_DATE = 0
    COL_DESCR = 1
    COL_ACC = 2
    COL_CONF = 3
    COL_DEBIT = 4
    COL_ASSET = 5
    COL_ACCU = 6

    COLOR_ROW_TRN_ODD = QtGui.QColor(255, 255, 255)
    COLOR_ROW_TRN_EVEN = QtGui.QColor(235, 255, 235)
    COLOR_ROW_UNBALANCED_TRN = QtGui.QColor(225, 225, 255)
    FONT_TRN = QtGui.QFont("Arial", weight=QtGui.QFont.Bold)

    CachedRow = namedtuple("CachedRow", ("trn", "item", "accu"))

    RowTypeRole = QtCore.Qt.UserRole

    RowTypeTransaction = 0
    RowTypeItem = 1
    AllRowTypes = (RowTypeTransaction, RowTypeItem)

    def __init__(self, account, parent=None):
        "Construct model for transactions related to given account."
        super().__init__(parent)
        if not isinstance(account, Account):
            raise TypeError()
        LOGGER.debug("Constructing transactions/items for %s" % account.fullname)
        self._account = account
        self._dirty = False
        self._rowCache = []
        self._rowCacheSize = len(self._rowCache)
        self._rowCacheDateRange = (None, None)
        self._updateRowCache()

    def refresh(self):
        "Refresh data of model from database"
        LOGGER.debug("Refresh rows for transactions/items in %s" % self._account.fullname)
        self.beginResetModel()
        self._updateRowCache()
        self.endResetModel()

    def _updateRowCache(self):
        "Update content of row cache."
        LOGGER.debug("Update cached rows for transactions/items in %s" % self._account.fullname)
        self._rowCache = []
        self._rowCacheSize = 0
        accu = 0
        for trn in self._account.filterTransactions():
            trnItems = list(trn)
            accFilter = FilterAccountsAndChildren(self._account)

            def itemkey(i):
                if accFilter.accepted(i):
                    return ["z" * 10]  # my account should ordered at last position
                else:
                    return i.account.fullname.lower().split(Account.SEPARATOR)

            trnItems.sort(key=itemkey)
            trnItemRows = []
            for item in trnItems:
                if self._account.isSelfOrHasChildAccount(item.account):
                    accu += item.value
                trnItemRows += [AccountTransactionsModel.CachedRow(None, item, None)]
            self._rowCache += [AccountTransactionsModel.CachedRow(trn, None, accu)]
            self._rowCache += trnItemRows
        self._rowCacheSize = len(self._rowCache)
        newDateRange = self._getRowCacheDateRange()
        if self._rowCacheDateRange != newDateRange:
            self._rowCacheDateRange = newDateRange
            self.dateRangeChanged.emit(*newDateRange)
        LOGGER.debug("Updated %d cached rows for %s" % (self._rowCacheSize, self._account.fullname))

    def _getRowCacheDateRange(self):
        "Get date range of all transactions"
        firstDate = datetime.date.max
        for trn, dummyItem, dummyAccu in self._rowCache:
            if trn is not None:
                firstDate = trn.date
                break
        lastDate = datetime.date.min
        for trn, dummyItem, dummyAccu in reversed(self._rowCache):
            if trn is not None:
                lastDate = trn.date
                break
        return (firstDate, lastDate)

    def _getRowCacheIdx(self, instance):
        "Get index of selected instance in row cache."
        for idx, cachedRow in enumerate(self._rowCache):
            if cachedRow.trn == instance or cachedRow.item == instance:
                return idx
        return -1

    def _getRowCacheTrnIdx(self, transaction):
        "Get index of selected transaction in row cache."
        idx = 0
        for cachedRow in self._rowCache:
            if cachedRow.trn == transaction:
                return idx
            if cachedRow.trn is not None:
                idx += 1
        return -1

    def _getRowCacheTrnSpan(self, trn):
        "Get number of rows used by transaction ( and it's items ) in row cache."
        trnFirstIdx = self._getRowCacheIdx(trn)
        trnLastIdx = -1
        if trnFirstIdx != -1:
            trnLastIdx = trnFirstIdx
            while trnLastIdx + 1 < len(self._rowCache) and self._rowCache[trnLastIdx + 1][1]:
                trnLastIdx += 1
        return (trnFirstIdx, trnLastIdx)

    def getAccount(self):
        "Return model's account."
        return self._account

    def getDateRange(self):
        return self._getRowCacheDateRange()

    def filterAcceptsRow(self, row, filter_):
        "Return true when given row is accepted by filter"
        if filter_ is None:
            return True
        if row >= self._rowCacheSize:
            return False
        cachedRow = self._rowCache[row]
        accept = False
        if cachedRow.item is not None:
            accept = filter_.accepted(cachedRow.item)
        elif cachedRow.trn is not None:
            accept = filter_.accepted(cachedRow.trn)
        return accept

    def setDirty(self, isDirty):
        "Set whether model has been altered and may require saving."
        self._dirty = isDirty
        self.dirty.emit(self._dirty)

    def isDirty(self):
        "Return true when model has been altered."
        return self._dirty

    def rowCount(self, parentIdx):
        if parentIdx.isValid():
            return 0
        return self._rowCacheSize

    def balanceTransaction(self, idx):
        "Adjust item at given index to balance transaction"
        if not idx.isValid():
            return
        row = self._rowCache[idx.row()]
        dummyTransaction, item, dummyAccu = row
        if item is not None:
            trn = item.transaction
            if not trn.isBalanced():
                # adjust current item to fix balance
                bal = trn.getBalance()
                val = item.value - bal
                self.setData(self.index(idx.row(), AccountTransactionsModel.COL_ASSET), val, QtCore.Qt.EditRole)

    def addTransaction(self, date, descr="", value=None, confirmed=None):
        "Add new transaction using given values"
        trn = Transaction(date)
        db = self._account.db
        db += trn
        item = Item(descr, value)
        item += self._account
        if confirmed is not None:
            item.setConfirmed(confirmed)
        trn += item
        self._updateRowCache()
        firstRow = self._getRowCacheIdx(trn)
        self.beginInsertRows(QtCore.QModelIndex(), firstRow, firstRow + 1)
        self.endInsertRows()
        self.setDirty(True)

    def addTransactionItem(self, idx, descr="", value=None, confirmed=None):
        "Add new item to transaction corresponding to given index"
        if not idx.isValid():
            return
        row = self._rowCache[idx.row()]
        transaction, item, dummyAccu = row
        newItem = None
        if transaction is not None:
            newItem = Item(descr, value)
            if confirmed is not None:
                newItem.setConfirmed(confirmed)
            transaction += newItem
            newItem += self._account
            if value is None and not transaction.isBalanced():
                # try to balance transaction when new item has been added
                newItem.setValue(-transaction.getBalance())
        elif item is not None:
            trn = item.transaction
            newItem = Item(descr, value)
            if confirmed is not None:
                newItem.setConfirmed(confirmed)
            trn += newItem
            newItem += self._account
            if value is None and not trn.isBalanced():
                # try to balance transaction when new item has been added
                newItem.setValue(-trn.getBalance())
        if newItem:
            self._updateRowCache()
            firstRow = self._getRowCacheIdx(newItem)
            self.beginInsertRows(QtCore.QModelIndex(), firstRow, firstRow)
            self.endInsertRows()
            self.setDirty(True)

    def changeTransactionItem(self, idx, date, descr="", value=None, confirmed=None):
        "Change item at given idx with selected values"
        if not idx.isValid():
            return
        idxRow = idx.row()
        row = self._rowCache[idxRow]
        trn, item, dummyAccu = row
        if trn is not None:
            # use first item in transaction of current account instead
            for trnItem in trn.filterItems(FilterAccounts(self._account)):
                item = trnItem
                idxRow = self._getRowCacheIdx(item)
                break
        if item is not None:
            self.setData(self.index(idxRow, AccountTransactionsModel.COL_CONF), confirmed, QtCore.Qt.CheckStateRole)
            self.setData(self.index(idxRow, AccountTransactionsModel.COL_ASSET), value, QtCore.Qt.EditRole)
            self.setData(self.index(idxRow, AccountTransactionsModel.COL_DESCR), descr, QtCore.Qt.EditRole)
            self.setData(self.index(idxRow, AccountTransactionsModel.COL_DATE), date, QtCore.Qt.EditRole)

    def findRow(self, filter_=None, date=None):
        "Return index first matched row by given filter or just near given date"
        if filter_ is not None:
            matched = []
            for idx, (trn, item, dummyAccu) in enumerate(self._rowCache):
                if item is not None:
                    if filter_.accepted(item):
                        if date is None:
                            return self.index(idx, AccountTransactionsModel.COL_DATE)
                        matched += [(item.date, idx, AccountTransactionsModel.COL_DESCR)]
                elif trn is not None:
                    if filter_.accepted(trn):
                        if date is None:
                            return self.index(idx, AccountTransactionsModel.COL_DATE)
                        matched += [(trn.date, idx, AccountTransactionsModel.COL_DATE)]
            nearDate = datetime.timedelta.max
            nearIdx = -1
            nearCol = 0
            if date is not None:
                for edate, eidx, ecol in matched:
                    dt = abs(edate - date)
                    if dt < nearDate:
                        nearDate = dt
                        nearIdx = eidx
                        nearCol = ecol
                if nearIdx != -1:
                    return self.index(nearIdx, nearCol)
        if date is not None:
            nearDate = (datetime.timedelta.max, -1)
            for idx, (trn, item, dummyAccu) in enumerate(self._rowCache):
                if trn is not None:
                    dt = abs(trn.date - date)
                    if dt < nearDate[0]:
                        nearDate = (dt, idx)
            if nearDate[1] != -1:
                return self.index(nearDate[1], AccountTransactionsModel.COL_DATE)
        return QtCore.QModelIndex()

    def insertRow(self, row, parentIdx=QtCore.QModelIndex()):
        "Return true when new row has been added to parent index."
        if row < 0:
            # add the first transaction for this account
            self.addTransaction(datetime.date.today())
            return True
        else:
            cachedRow = self._rowCache[row]
            transaction, item, dummyAccu = cachedRow
            if transaction is not None:
                self.addTransaction(transaction.date)
                return True
            elif item is not None:
                self.addTransactionItem(self.index(row, 0))
                return True
        return False

    def removeRow(self, row, parentIdx=QtCore.QModelIndex()):
        "Return true when row from parent index has been removed."
        if row < 0 or row >= len(self._rowCache):
            return False
        cachedRow = self._rowCache[row]
        changed = False
        if cachedRow.trn is not None:
            trnRows = self._getRowCacheTrnSpan(cachedRow.trn)
            self.beginRemoveRows(parentIdx, trnRows[0], trnRows[1])
            db = self._account.db
            db -= cachedRow.trn
            self._updateRowCache()
            self.endRemoveRows()
            changed = True
        elif cachedRow.item is not None:
            currAccItems = list(filter(lambda it: self._account.isSelfOrHasChildAccount(it.account),
                                       cachedRow.item.transaction))
            if self._account.isSelfOrHasChildAccount(cachedRow.item.account) and len(currAccItems) == 1:
                # there is just one item for current account
                # removing this item will remove it's transaction from our account too
                trnRows = self._getRowCacheTrnSpan(cachedRow.item.transaction)
                self.beginRemoveRows(parentIdx, trnRows[0], trnRows[1])
            else:
                # there are multiple items for current account
                # removing this item will not remove it's transaction from our account too
                self.beginRemoveRows(parentIdx, row, row)
            trn = cachedRow.item.transaction
            trn -= cachedRow.item
            self._updateRowCache()
            self.endRemoveRows()
            changed = True
        if changed:
            self.setDirty(True)
        return changed

    def columnCount(self, parent):
        return 7

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or index.row() >= self._rowCacheSize:
            return None
        colIdx = index.column()
        cachedRow = self._rowCache[index.row()]
        if role == QtCore.Qt.DisplayRole:
            if cachedRow.trn is not None:
                if colIdx == AccountTransactionsModel.COL_DATE:
                    return cachedRow.trn.date.strftime("%a %d. %b %Y")
                elif colIdx == AccountTransactionsModel.COL_DESCR:
                    return cachedRow.trn.descr
                elif colIdx == AccountTransactionsModel.COL_ACCU:
                    return str(cachedRow.accu)
            elif cachedRow.item is not None:
                if colIdx == AccountTransactionsModel.COL_DESCR:
                    return cachedRow.item.descr
                elif colIdx == AccountTransactionsModel.COL_ACC:
                    return cachedRow.item.account.fullname
                elif colIdx == AccountTransactionsModel.COL_ASSET:
                    if cachedRow.item.value >= 0:
                        return str(cachedRow.item.value)
                elif colIdx == AccountTransactionsModel.COL_DEBIT:
                    if cachedRow.item.value < 0:
                        return str(abs(cachedRow.item.value))
        elif role == QtCore.Qt.CheckStateRole:
            if cachedRow.item is not None:
                if colIdx == AccountTransactionsModel.COL_CONF:
                    return QtCore.Qt.Checked if cachedRow.item.confirmed else QtCore.Qt.Unchecked
        elif role == QtCore.Qt.EditRole:
            if cachedRow.trn is not None:
                if colIdx == AccountTransactionsModel.COL_DATE:
                    return cachedRow.trn.date
                elif colIdx == AccountTransactionsModel.COL_DESCR:
                    return cachedRow.trn
            elif cachedRow.item is not None:
                if colIdx == AccountTransactionsModel.COL_ACC:
                    return cachedRow.item.account.fullname
                elif colIdx == AccountTransactionsModel.COL_DESCR:
                    return cachedRow.item
                elif colIdx == AccountTransactionsModel.COL_ASSET:
                    return str(cachedRow.item.value)
                elif colIdx == AccountTransactionsModel.COL_DEBIT:
                    return str(-cachedRow.item.value)
        elif role == QtCore.Qt.BackgroundRole:
            if cachedRow.trn is not None:
                if not cachedRow.trn.isBalanced():
                    return AccountTransactionsModel.COLOR_ROW_UNBALANCED_TRN
                trnIdx = self._getRowCacheTrnIdx(cachedRow.trn)
            elif cachedRow.item is not None:
                trnIdx = self._getRowCacheTrnIdx(cachedRow.item.transaction)
            if trnIdx % 2:
                return AccountTransactionsModel.COLOR_ROW_TRN_ODD
            else:
                return AccountTransactionsModel.COLOR_ROW_TRN_EVEN
        elif role == QtCore.Qt.FontRole:
            if cachedRow.trn is not None:
                return AccountTransactionsModel.FONT_TRN
        elif role == QtCore.Qt.TextAlignmentRole:
            if colIdx in [AccountTransactionsModel.COL_ASSET,
                          AccountTransactionsModel.COL_DEBIT,
                          AccountTransactionsModel.COL_ACCU]:
                return QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight
            else:
                return QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft
            return QtCore.Qt.AlignVCenter
        elif role == QtCore.Qt.ToolTipRole:
            t = ""
            b = ""
            if cachedRow.trn is not None:
                if colIdx == AccountTransactionsModel.COL_DESCR:
                    t = cachedRow.trn.descr
            elif cachedRow.item is not None:
                if colIdx == AccountTransactionsModel.COL_DESCR:
                    t = cachedRow.item.descr
            if cachedRow.trn is not None:
                if not cachedRow.trn.isBalanced():
                    b = -cachedRow.trn.getBalance()
            elif cachedRow.item is not None:
                if not cachedRow.item.transaction.isBalanced():
                    b = -cachedRow.item.transaction.getBalance()
            if t and b:
                return "<b>Transaction unbalanced by %s</b><br>%s" % (b, t)
            elif t:
                return t
            elif b:
                return b
        elif role == AccountTransactionsModel.RowTypeRole:
            if cachedRow.trn is not None:
                return AccountTransactionsModel.RowTypeTransaction
            elif cachedRow.item is not None:
                return AccountTransactionsModel.RowTypeItem
        return None

    def setData(self, idx, value, role=QtCore.Qt.EditRole):
        if not idx.isValid():
            return False
        colIdx = idx.column()
        cachedRow = self._rowCache[idx.row()]
        changed = False
        accuChanged = False
        trnMoved = None
        itemMoved = None
        if role == QtCore.Qt.EditRole:
            if cachedRow.trn is not None:
                oldTrnRows = self._getRowCacheTrnSpan(cachedRow.trn)
                if colIdx == AccountTransactionsModel.COL_DATE:
                    changed = cachedRow.trn.setDate(value)
                    trnMoved = cachedRow.trn
                elif colIdx == AccountTransactionsModel.COL_DESCR:
                    changed = cachedRow.trn.setDescr(str(value))
            elif cachedRow.item is not None:
                oldTrnRows = self._getRowCacheTrnSpan(cachedRow.item.transaction)
                if colIdx == AccountTransactionsModel.COL_DATE:
                    changed = cachedRow.item.transaction.setDate(value)
                    trnMoved = cachedRow.trn
                elif colIdx == AccountTransactionsModel.COL_ACC:
                    oldAcc = cachedRow.item.account
                    accName = str(value)
                    if not accName in oldAcc.db:
                        return False
                    newAcc = oldAcc.db[accName]
                    if oldAcc != newAcc:
                        oldAcc -= cachedRow.item
                        newAcc += cachedRow.item
                        changed = True
                        itemMoved = cachedRow.item
                elif colIdx == AccountTransactionsModel.COL_DESCR:
                    changed = cachedRow.item.setDescr(str(value))
                elif colIdx == AccountTransactionsModel.COL_ASSET:
                    if isinstance(value, Decimal):
                        changed = cachedRow.item.setAsset(value)
                    else:
                        changed = cachedRow.item.setAsset(str(value))
                    accuChanged = changed
                elif colIdx == AccountTransactionsModel.COL_DEBIT:
                    if isinstance(value, Decimal):
                        changed = cachedRow.item.setDebit(value)
                    else:
                        changed = cachedRow.item.setDebit(str(value))
                    accuChanged = changed
        elif role == QtCore.Qt.CheckStateRole:
            if cachedRow.item is not None:
                if colIdx == AccountTransactionsModel.COL_CONF:
                    if isinstance(value, bool):
                        changed = cachedRow.item.setConfirmed(value)
                    else:
                        changed = cachedRow.item.setConfirmed(bool(value))
        if changed:
            self.setDirty(True)
        if trnMoved or itemMoved or accuChanged:
            self._updateRowCache()
        if trnMoved or itemMoved:
            pidx = QtCore.QModelIndex()
            if itemMoved:
                oldItemRow = idx.row()
                newItemRow = self._getRowCacheIdx(itemMoved)
                if newItemRow == oldItemRow:
                    pass  # no change
                elif newItemRow >= 0:
                    destinationChild = newItemRow + (1 if oldItemRow < newItemRow else 0)
                    self.beginMoveRows(pidx, oldItemRow, oldItemRow, pidx, destinationChild)
                    self.endMoveRows()
                    changed = False
                else:
                    accuChanged = True
                    newTrnRows = self._getRowCacheTrnSpan(itemMoved.transaction)
                    if newTrnRows[0] >= 0:
                        self.beginRemoveRows(pidx, idx.row(), idx.row())
                    else:
                        self.beginRemoveRows(pidx, oldTrnRows[0], oldTrnRows[1])
                    self.endRemoveRows()
                    changed = False
            if trnMoved:
                newTrnRows = self._getRowCacheTrnSpan(trnMoved)
                if newTrnRows != oldTrnRows:
                    firstMovedRow = oldTrnRows[0]
                    lastMovedRow = oldTrnRows[1]
                    nofMovedRows = lastMovedRow - firstMovedRow + 1
                    destRow = newTrnRows[0]
                    if destRow > firstMovedRow and destRow < lastMovedRow:
                        # overlapping move area, move remainder instead
                        firstMovedRow = oldTrnRows[1] + 1
                        nofMovedRows = newTrnRows[0] - oldTrnRows[0]
                        lastMovedRow = firstMovedRow + nofMovedRows - 1
                        destRow -= nofMovedRows
                    elif oldTrnRows[0] < newTrnRows[0]:
                        destRow += 1  # need to tweak destination index to comply with QAbstractItemModel.beginMoveRows()
                    self.beginMoveRows(pidx, firstMovedRow, lastMovedRow, pidx, destRow)
                    self.endMoveRows()
                    accuChanged = True
                    changed = False
        if accuChanged:
            self.dataChanged.emit(self.index(0, AccountTransactionsModel.COL_ACC),
                                  self.index(len(self._rowCache) - 1, AccountTransactionsModel.COL_ACC))
        if changed:
            self.dataChanged.emit(idx, idx)
        return changed

    def headerData(self, section, orientation, role):
        "Return row/column header."
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            if orientation == QtCore.Qt.Vertical:
                return str(section + 1)
            if orientation == QtCore.Qt.Horizontal:
                if section == AccountTransactionsModel.COL_DATE:
                    return "Date"
                elif section == AccountTransactionsModel.COL_CONF:
                    return u"✓"
                elif section == AccountTransactionsModel.COL_DESCR:
                    return "Description"
                elif section == AccountTransactionsModel.COL_ACC:
                    return "Account"
                elif section == AccountTransactionsModel.COL_ASSET:
                    return "Asset"
                elif section == AccountTransactionsModel.COL_DEBIT:
                    return "Debit"
                elif section == AccountTransactionsModel.COL_ACCU:
                    return "Value"
        return None

    def flags(self, idx):
        if idx.row() < 0 or idx.row() >= self._rowCacheSize:
            return QtCore.Qt.NoItemFlags
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        colIdx = idx.column()
        cachedRow = self._rowCache[idx.row()]
        canEdit = False
        canCheck = False
        if cachedRow.trn is not None:
            if colIdx == AccountTransactionsModel.COL_DATE:
                canEdit = True
            elif colIdx == AccountTransactionsModel.COL_DESCR:
                canEdit = True
        elif cachedRow.item is not None:
            if colIdx == AccountTransactionsModel.COL_DESCR:
                canEdit = True
            elif colIdx == AccountTransactionsModel.COL_ACC:
                canEdit = True
            elif colIdx == AccountTransactionsModel.COL_CONF:
                canCheck = True
            elif colIdx == AccountTransactionsModel.COL_ASSET:
                canEdit = True
            elif colIdx == AccountTransactionsModel.COL_DEBIT:
                canEdit = True
        if canEdit:
            flags |= QtCore.Qt.ItemIsEditable
        if canCheck:
            flags |= QtCore.Qt.ItemIsUserCheckable
        return flags


class CustomTransactionFilter(QtCore.QSortFilterProxyModel):
    "Implement custom filter for AccountTransactionModel"

    # Whether model has been altered and needs saving
    dirty = QtCore.pyqtSignal(bool)

    # signal change of first/last transaction's date
    dateRangeChanged = QtCore.pyqtSignal(datetime.date, datetime.date)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter = None

    def getAccount(self):
        return self.sourceModel().getAccount()

    def getDateRange(self):
        return self.sourceModel().getDateRange()

    def setDirty(self, isDirty):
        self.sourceModel().setDirty(isDirty)

    def isDirty(self):
        return self.sourceModel().isDirty()

    def findRow(self, filter_=None, date=None):
        srcIdx = self.sourceModel().findRow(filter_, date)
        return self.mapFromSource(srcIdx)

    def setSourceModel(self, model):
        if not isinstance(model, AccountTransactionsModel):
            raise TypeError("Expected AccountTransactionsModel")
        super().setSourceModel(model)
        model.dirty.connect(self.dirty)
        model.dateRangeChanged.connect(self.dateRangeChanged)

    def filter(self, filter_):
        "Apply given filter constraints"
        changed = self._filter != filter_
        self._filter = filter_
        if changed:
            self.invalidateFilter()

    def filterAcceptsRow(self, srcRow, srcParentIdx):
        return self.sourceModel().filterAcceptsRow(srcRow, self._filter)

    def insertRow(self, row, parentIdx=QtCore.QModelIndex()):
        myidx = self.index(row, 0)
        srcidx = self.mapToSource(myidx)
        row = srcidx.row()
        return self.sourceModel().insertRow(row, self.mapToSource(parentIdx))

    def removeRow(self, row, parentIdx=QtCore.QModelIndex()):
        idx = self.index(row, 0)
        idx = self.mapToSource(idx)
        row = idx.row()
        return self.sourceModel().removeRow(row, self.mapToSource(parentIdx))

    def data(self, idx, role=QtCore.Qt.DisplayRole):
        idx = self.mapToSource(idx)
        return self.sourceModel().data(idx, role)

    def setData(self, idx, value, role=QtCore.Qt.EditRole):
        idx = self.mapToSource(idx)
        return self.sourceModel().setData(idx, value, role)

    def balanceTransaction(self, idx):
        idx = self.mapToSource(idx)
        return self.sourceModel().balanceTransaction(idx)

    def addTransaction(self, **kwargs):
        return self.sourceModel().addTransaction(**kwargs)

    def addTransactionItem(self, idx, **kwargs):
        idx = self.mapToSource(idx)
        return self.sourceModel().addTransactionItem(idx, **kwargs)

    def changeTransactionItem(self, idx, **kwargs):
        idx = self.mapToSource(idx)
        return self.sourceModel().changeTransactionItem(idx, **kwargs)


class ImporterEntriesModel(QtCore.QAbstractItemModel):
    "Represents model of entries that can be imported"

    COL_DATE = 0
    COL_DESCR = 1
    COL_VALUE = 2

    EntryRole = QtCore.Qt.UserRole

    FONT = QtGui.QFont("Arial")

    def __init__(self, entries, parent=None):
        "Construct model from given list of entries"
        super().__init__(parent)
        self._entries = entries

    def index(self, row, col, parent=QtCore.QModelIndex()):
        "Return index at given row and column in model with given parent"
        if row < len(self._entries):
            return self.createIndex(row, col, self._entries[row])
        return QtCore.QModelIndex()

    def parent(self, idx):
        return QtCore.QModelIndex()

    def rowCount(self, idx):
        if idx.isValid():
            return 0
        else:
            return len(self._entries)

    def columnCount(self, idx):
        if idx.isValid():
            return 0
        else:
            return 3

    def data(self, idx, role):
        if not idx.isValid():
            return None
        entry = idx.internalPointer()
        if role == QtCore.Qt.DisplayRole:
            if idx.column() == ImporterEntriesModel.COL_DATE:
                return entry.date.strftime("%a %d. %b %Y")
            elif idx.column() == ImporterEntriesModel.COL_DESCR:
                return entry.descr
            elif idx.column() == ImporterEntriesModel.COL_VALUE:
                return str(entry.value)
        elif role == QtCore.Qt.ToolTipRole:
            if idx.column() == ImporterEntriesModel.COL_DESCR:
                return entry.descr
        elif role == ImporterEntriesModel.EntryRole:
            return entry
        elif role == QtCore.Qt.TextAlignmentRole:
            if idx.column() == ImporterEntriesModel.COL_VALUE:
                return QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight
            else:
                return QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft
            return QtCore.Qt.AlignVCenter
        elif role == QtCore.Qt.FontRole:
            return ImporterEntriesModel.FONT

    def headerData(self, section, orientation, role):
        "Return row/column header."
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            if orientation == QtCore.Qt.Vertical:
                return str(section + 1)
            if orientation == QtCore.Qt.Horizontal:
                if section == ImporterEntriesModel.COL_DATE:
                    return "Date"
                elif section == ImporterEntriesModel.COL_DESCR:
                    return "Description"
                elif section == ImporterEntriesModel.COL_VALUE:
                    return "Value"
        return None

    def removeRow(self, row, parentIdx=QtCore.QModelIndex()):
        "Return true when row has been removed."
        if row < 0 or row >= len(self._entries):
            return False
        self.beginRemoveRows(parentIdx, row, row)
        del self._entries[row]
        self.endRemoveRows()
        return True


class AnyStringFilteredModel(QtCore.QSortFilterProxyModel):
    "Filter rows case-insensitive that share given string"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.txt = ""

    def filterAcceptsRow(self, sourceRow, sourceParent):
        index0 = self.sourceModel().index(sourceRow, 0, sourceParent)
        txt = self.sourceModel().data(index0, QtCore.Qt.DisplayRole).lower()
        return self.txt in txt
