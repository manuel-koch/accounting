# -*- coding: utf-8 -*-
'''
Table of transaction items to be imported.

@author: Manuel Koch
'''
import logging

from PyQt5 import QtGui, QtWidgets, QtCore

from accounting.importer.base import ImporterEntry
from accounting.gui.models import ImporterEntriesModel

LOGGER = logging.getLogger(__name__)


class TransactionImportTable(QtWidgets.QTableView):
    MIN_COL_WIDTHS = (  # column using minimum width
        (ImporterEntriesModel.COL_DATE, 120),
        (ImporterEntriesModel.COL_VALUE, 80),
    )

    SPREAD_COL_WIDTHS = (  # column spreading remaining space by factor
        (ImporterEntriesModel.COL_DESCR, 1),
    )

    entrySelected = QtCore.pyqtSignal(ImporterEntry)
    entryDeselected = QtCore.pyqtSignal()
    addAsTransaction = QtCore.pyqtSignal()
    addAsItem = QtCore.pyqtSignal()
    applyToItem = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.verticalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
        self.verticalHeader().setDefaultSectionSize(24)
        font = self.verticalHeader().font()
        font.setPointSize(10);
        self.verticalHeader().setFont(font)
        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)

    def keyboardSearch(self, *args, **kwargs):
        pass  # disable search feature

    def resizeEvent(self, resizeEvent):
        super().resizeEvent(resizeEvent)
        self.adjustColumnWidths()

    def selectionChanged(self, selected, deselected):
        super().selectionChanged(selected, deselected)
        if selected.count():
            idx = selected.indexes()[0]
            entry = self.model().data(idx, ImporterEntriesModel.EntryRole)
            self.entrySelected.emit(entry)
        else:
            self.entryDeselected.emit()

    def adjustColumnWidths(self):
        "Adjust width of all columns to use all available space."
        hw = self.horizontalHeader().size().width()
        for colIdx, minWidth in TransactionImportTable.MIN_COL_WIDTHS:
            colWidth = minWidth
            hw -= colWidth
            self.setColumnWidth(colIdx, colWidth)
        fSum = sum([w[1] for w in TransactionImportTable.SPREAD_COL_WIDTHS])
        for colIdx, factor in TransactionImportTable.SPREAD_COL_WIDTHS:
            colWidth = hw * factor / fSum
            self.setColumnWidth(colIdx, colWidth)

    def keyPressEvent(self, keyEvent):
        "Handle key press event."
        idx = self.currentIndex()
        if idx.isValid():
            if keyEvent.key() == QtCore.Qt.Key_Minus:
                self.model().removeRow(idx.row())
            elif keyEvent.key() == QtCore.Qt.Key_T:
                self.addAsTransaction.emit()
            elif keyEvent.key() == QtCore.Qt.Key_I:
                if keyEvent.modifiers() & QtCore.Qt.ShiftModifier:
                    self.applyToItem.emit()
                else:
                    self.addAsItem.emit()
            else:
                super().keyPressEvent(keyEvent)
        elif keyEvent.key() == QtCore.Qt.Key_Escape:
            self.clearSelection()
        else:
            super().keyPressEvent(keyEvent)
