# -*- coding: utf-8 -*-
'''
View of transaction items to be imported.

@author: Manuel Koch
'''
import logging

from PyQt5 import QtGui, QtWidgets, QtCore

from accounting.importer.base        import ImporterEntry
from accounting.gui.models           import ImporterEntriesModel
from accounting.gui.widget.imptable  import TransactionImportTable
from accounting.gui.widget.impwizard import TransactionImportWizard


LOGGER = logging.getLogger(__name__)


class TransactionImportView(QtWidgets.QWidget):

    # importing finished
    importDone = QtCore.pyqtSignal()

    # import entry selected
    importEntrySelected   = QtCore.pyqtSignal(ImporterEntry)
    importEntryDeselected = QtCore.pyqtSignal()

    # add given entry as new transaction
    importEntryAsTransaction = QtCore.pyqtSignal(ImporterEntry)

    # add given entry to transaction
    importEntryAsItem = QtCore.pyqtSignal(ImporterEntry)

    # apply given entry to item
    importEntryToItem = QtCore.pyqtSignal(ImporterEntry)

    KIND_ASSET = 0
    KIND_DEBIT = 1
    
    MARGIN_LEFT = 57
    
    def __init__(self):
        "Construct view to jump to transactions for importing."
        super().__init__()

        hbox = QtWidgets.QHBoxLayout()
        hbox.setContentsMargins( TransactionImportView.MARGIN_LEFT, 0, 0, 0 )
        hbox.setSpacing(2)

        self._tbl = TransactionImportTable()
        self._tbl.entrySelected.connect( self.importEntrySelected )
        self._tbl.entryDeselected.connect( self.importEntryDeselected )
        self._tbl.addAsTransaction.connect( self._importEntryAsTransaction )
        self._tbl.addAsItem.connect( self._importEntryAsItem )
        self._tbl.applyToItem.connect( self._importEntryToItem )
        hbox.addWidget(self._tbl)
        
        vbox = QtWidgets.QVBoxLayout()
        vbox.setContentsMargins( 0, 0, 0, 0 )
        hbox.setSpacing(2)
        
        btn = QtWidgets.QPushButton("Add as transaction")
        btn.pressed.connect( self._importEntryAsTransaction )
        vbox.addWidget( btn )
        
        btn = QtWidgets.QPushButton("Add to transaction")
        btn.pressed.connect( self._importEntryAsItem )
        vbox.addWidget( btn )
        
        btn = QtWidgets.QPushButton("Apply to item")
        btn.pressed.connect( self._importEntryToItem )
        vbox.addWidget( btn )
        
        vbox.addSpacing( 4 )
        
        hboxBtns = QtWidgets.QHBoxLayout()
        hboxBtns.addWidget( QtWidgets.QLabel("Value type:") )
        self._kindBtnGrp = QtWidgets.QButtonGroup()
        cb = QtWidgets.QCheckBox("Debit")
        cb.setToolTip("Values are debit")
        self._kindBtnGrp.addButton( cb, TransactionImportView.KIND_DEBIT )
        hboxBtns.addWidget( cb )
        cb = QtWidgets.QCheckBox("Asset")
        cb.setChecked( True )
        cb.setToolTip("Values are asset")
        self._kindBtnGrp.addButton( cb, TransactionImportView.KIND_ASSET )
        hboxBtns.addWidget( cb )
        vbox.addLayout( hboxBtns )
        
        self._confirmCb = QtWidgets.QCheckBox("Confirm added/applied item")
        self._confirmCb.setChecked( True )
        vbox.addWidget( self._confirmCb )
        vbox.addSpacing(5)
        self._filterCb = QtWidgets.QRadioButton("Filter transaction(s)")
        self._filterCb.setToolTip("Only display transaction(s) that match current selected import entry")
        self._filterCb.setChecked( True )
        self._jumpCb = QtWidgets.QRadioButton("Jump to transaction")
        self._jumpCb.setToolTip("Jump to transaction that matches current selected import entry")
        self._filterBtgrp = QtWidgets.QButtonGroup()
        self._filterBtgrp.buttonClicked.connect( self._filterChanged )
        self._filterBtgrp.addButton(self._filterCb)
        self._filterBtgrp.addButton(self._jumpCb)
        vbox.addWidget( self._filterCb )
        vbox.addWidget( self._jumpCb )
        vbox.addSpacing(5)
        self._dateOnlyCb = QtWidgets.QCheckBox("Filter by date only")
        self._dateOnlyCb.setToolTip("Only filter / jump to transaction(s) that match current selected date")
        vbox.addWidget( self._dateOnlyCb )
        
        vbox.addStretch( 1 )
        
        btn = QtWidgets.QPushButton("Done")
        btn.pressed.connect( self.importDone )
        vbox.addWidget( btn )
        hbox.addLayout( vbox )
        
        self.setLayout( hbox )
                
        self._wizard = TransactionImportWizard()
        self._wizard.accepted.connect( self._wizardAccepted )
        self._wizard.rejected.connect( self.stopImport )

    def filterOnSelection(self):
        "Return true when selection change should result in filtering"
        return self._filterCb.isChecked()
    
    def filterByDateOnly(self):
        "Return true when filtering should only use date"
        return self._dateOnlyCb.isChecked()

    def startImport(self):
        "Trigger start of import of transaction data for current account"
        self._wizard.restart()
        self._wizard.show()
        
    def _wizardAccepted(self):
        "User accepted wizard, proceed with import and apply imported entries to our table"
        self._tbl.setModel( self._wizard.getImporterEntriesModel() )
        self.show()
    
    def _filterChanged(self,btn):
        "Handle change if filter mode"
        entries = self._currImportEntries()[:1]
        if entries:
            self.importEntrySelected.emit( entries[0] )
    
    def _currImportEntries(self):
        "Get instances of ImporterEntry from current selected rows"
        indices = self._tbl.selectionModel().selectedRows()
        entries = []
        for idx in indices:
            if idx.isValid():
                entry = self._tbl.model().data( idx, ImporterEntriesModel.EntryRole )
                entry.setConfirmed( self._confirmCb.isChecked() )
                if self._kindBtnGrp.checkedId() == TransactionImportView.KIND_DEBIT:
                    entry.inverseValue()
                entries += [entry]
        return entries 
        
    def _importEntryAsTransaction(self):
        "Trigger adding current selected entry as new transaction"
        entries = self._currImportEntries()
        self.importEntryAsTransaction.emit( entries[0] )
        for entry in entries[1:]:
            self.importEntryAsItem.emit( entry )
        
    def _importEntryToItem(self):
        "Trigger applying current selected entry to item"
        for entry in self._currImportEntries()[:1]:
            self.importEntryToItem.emit( entry )

    def _importEntryAsItem(self):
        "Trigger adding current selected entry to transaction"
        for entry in self._currImportEntries():
            self.importEntryAsItem.emit( entry )

    def stopImport(self):
        "Trigger end of import of transaction data for current account"
        self._tbl.setModel( None )
        self.importDone.emit()

