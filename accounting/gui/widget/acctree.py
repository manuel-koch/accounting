# -*- coding: utf-8 -*-
'''
Account tree widget

@author: Manuel Koch
'''

from PyQt5 import QtGui, QtWidgets, QtCore


from accounting.core.core import Account
from accounting.gui.models import AccountModel

class AccountTree(QtWidgets.QTreeView):
    
    # Whether model has been altered and needs saving
    dirty = QtCore.pyqtSignal(bool)

    # User triggered creation of reports for current selected accounts
    createReport = QtCore.pyqtSignal()

    # User triggered import data on current selected account
    importData = QtCore.pyqtSignal()

    # User triggered opening details for given account
    showAccount = QtCore.pyqtSignal(Account)
    
    # User triggered editing details of given account
    editAccount = QtCore.pyqtSignal(Account)

    def __init__(self):
        "Construct account tree view."
        super().__init__()
        self.setMinimumWidth(100)
        self.setMaximumWidth(250)
        self.setSortingEnabled(True)
        self.sortByColumn( 0, QtCore.Qt.AscendingOrder )
        self.setContextMenuPolicy( QtCore.Qt.CustomContextMenu )
        self.customContextMenuRequested.connect( self.openContextMenu )
        self.setEditTriggers( self.EditKeyPressed )
        self.setExpandsOnDoubleClick(False)
        self.setSelectionMode( QtWidgets.QAbstractItemView.ExtendedSelection )
        self.doubleClicked.connect( self._onDblClicked )
        self._model       = None
        self._sortedmodel = None
        
    def setDatabase(self,db):
        "Set database for tree view."
        if db:
            self._model = AccountModel( db )
            self._model.dirty.connect( self.dirty )
            self._model.rowsInserted.connect( self._onRowsInserted )
            self._sortedmodel = QtCore.QSortFilterProxyModel()
            self._sortedmodel.setDynamicSortFilter( True )
            self._sortedmodel.setSourceModel( self._model )
            self.setModel( self._sortedmodel )
        else:
            self.setModel( None )

    def setDirty(self,isDirty):
        "Set whether model has been altered and may require saving."
        if self._model:
            self._model.setDirty(isDirty)
        
    def isDirty(self):
        "Return true when model has been altered."
        if self._model:
            return self._model.isDirty()
        else:
            return False
    
    def _onDblClicked(self):
        "Handle double click on tree item"
        sidx = self.currentIndex()
        idx  = self._sortedmodel.mapToSource( sidx )
        acc  = self._model.data( idx, AccountModel.AccountRole )
        self.showAccount.emit( acc )
        
    def _onRowsInserted(self,pidx,firstrow,lastrow):
        "Handle insert of new account"
        sidx = self._sortedmodel.mapFromSource( pidx )
        self.setExpanded( sidx, True )

    def openContextMenu(self,position):
        "Handle request for context menu."
        indexes = self.selectedIndexes()
        menu = QtWidgets.QMenu()
        if indexes:
            if len(indexes)==1:
                menu.addAction(self.tr("Edit account"),self.menuEditAccount)
                menu.addAction(self.tr("New child account"),self.menuNewChildAccount)
                menu.addAction(self.tr("New sibling account"),self.menuNewSiblingAccount)
                menu.addAction(self.tr("Import data"),self.menuImportData)
            menu.addAction(self.tr("Create report"),self.menuCreateReport)
        else:
            menu.addAction(self.tr("New account"),self.menuNewChildAccount)
        menu.exec_(self.viewport().mapToGlobal(position))

    def menuEditAccount(self):
        "User triggered edit on current selected account"
        sidx = self.currentIndex()
        idx  = self._sortedmodel.mapToSource( sidx )
        acc  = self._model.data( idx, AccountModel.AccountRole )
        self.editAccount.emit( acc )

    def _newAccount(self,asChild):
        "Create a new account as child or sibling of current selected account."
        indexes = self.selectedIndexes()
        if indexes:
            sidx = indexes[0]
        else:
            sidx = QtCore.QModelIndex()
        if not asChild:
            sidx = self._sortedmodel.parent( sidx )
        idx = self._sortedmodel.mapToSource( sidx )
        self._model.insertRow( 0, idx )
        
    def menuNewChildAccount(self):
        "Add a new account as child of current selected account or add new account to database."
        self._newAccount(True)

    def menuNewSiblingAccount(self):
        "Add a new account as sibling of current selected account or add new account to database."
        self._newAccount(False)

    def menuCreateReport(self):
        "Create a new report for selected account(s)."
        self.createReport.emit()

    def menuImportData(self):
        "Import data into current account"
        self.importData.emit()

