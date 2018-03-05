# -*- coding: utf-8 -*-
'''
Delegates to edit table cells.

@author: Manuel Koch
'''

import datetime
import logging
from PyQt5 import QtGui, QtWidgets, QtCore

from accounting.core.core import Transaction, Item
from accounting.core.core import FilterGreaterOrEqualDate, FilterLessOrEqualDate
from accounting.gui.models import AnyStringFilteredModel

LOGGER = logging.getLogger(__name__)


class CustomDateEdit(QtWidgets.QDateEdit):
    """Enhance date edit widget to modify current date with +/- keys."""

    def __init__(self, parent):
        """Construct custom date edit widget."""
        super().__init__(parent)

    def keyPressEvent(self, keyEvent):
        """Adjust current date when +/- is pressed by one day."""
        super().keyPressEvent(keyEvent)
        sec = self.currentSection()
        if keyEvent.key() == QtCore.Qt.Key_Plus:
            if sec == QtWidgets.QDateEdit.DaySection:
                self.setDate(self.date().addDays(1))
            elif sec == QtWidgets.QDateEdit.MonthSection:
                self.setDate(self.date().addMonths(1))
            elif sec == QtWidgets.QDateEdit.YearSection:
                self.setDate(self.date().addYears(1))
        elif keyEvent.key() == QtCore.Qt.Key_Minus:
            if sec == QtWidgets.QDateEdit.DaySection:
                self.setDate(self.date().addDays(-1))
            elif sec == QtWidgets.QDateEdit.MonthSection:
                self.setDate(self.date().addMonths(-1))
            elif sec == QtWidgets.QDateEdit.YearSection:
                self.setDate(self.date().addYears(-1))
        elif keyEvent.key() == QtCore.Qt.Key_N or keyEvent.key() == QtCore.Qt.Key_T or \
                keyEvent.key() == QtCore.Qt.Key_J or keyEvent.key() == QtCore.Qt.Key_H:
            self.setDate(QtCore.QDate.currentDate())


class DateDelegate(QtWidgets.QStyledItemDelegate):
    """Provide editing functionality for date cell."""

    MIN_WIDTH = 120

    def createEditor(self, parent, option, index):
        """Create an editor widget suitable for editing model data at given index."""
        widget = CustomDateEdit(parent)
        widget.setCalendarPopup(True)
        widget.setDisplayFormat("ddd d. MMM yyyy")
        return widget

    def setEditorData(self, editor, index):
        """Apply model data from given index to editor widget."""
        data = self.parent().model().data(index, QtCore.Qt.EditRole)
        if data != None:
            editor.setDate(data)

    def setModelData(self, editor, model, index):
        """Apply data from editor to model."""
        d = editor.date()
        d = datetime.date(d.year(), d.month(), d.day())
        model.setData(index, d)

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)
        if s.width() < DateDelegate.MIN_WIDTH:
            s.setWidth(DateDelegate.MIN_WIDTH)
        return s


class AnyStringCompleter(QtWidgets.QCompleter):
    """A completer class that matches a string case-insensitive in the middle of available strings.
    Base QCompleter can only match a string at the beginning of available strings.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = None
        self._filteredModel = None

    def setModel(self, model):
        self._model = model
        self._filteredModel = AnyStringFilteredModel()
        self._filteredModel.setSourceModel(model)
        super().setModel(self._filteredModel)

    def splitPath(self, path):
        self._filteredModel.txt = str(path).lower()
        self._filteredModel.invalidateFilter()
        return []


class AccountDelegate(QtWidgets.QStyledItemDelegate):
    """Provide editing functionality for account cell."""

    MIN_WIDTH = 100

    def createEditor(self, parent, option, index):
        """Create an editor widget suitable for editing model data at given index."""
        accounts = self.parent().model().getAccount().db.getChildAccounts(True)
        fullnames = [acc.fullname for acc in accounts]
        fullnames.sort(key=str.lower)

        widget = QtWidgets.QComboBox(parent)
        widget.setEditable(True)
        widget.setInsertPolicy(widget.NoInsert)
        widget.setMaxVisibleItems(10)
        completer = AnyStringCompleter()
        completer.setModel(QtCore.QStringListModel(fullnames))
        widget.setCompleter(completer)
        return widget

    def setEditorData(self, editor, index):
        """Apply model data from given index to editor widget."""
        data = self.parent().model().data(index, QtCore.Qt.EditRole)
        editor.setCurrentIndex(editor.findText(data))

    def setModelData(self, editor, model, index):
        """Apply data from editor to model."""
        fullname = editor.currentText()
        model.setData(index, fullname)

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)
        if s.width() < AccountDelegate.MIN_WIDTH:
            s.setWidth(AccountDelegate.MIN_WIDTH)
        return s


class CustomDescrComboBox(QtWidgets.QComboBox):
    """Enhance combo box widget to jump to entries with down/up keys."""

    def __init__(self, parent):
        """Construct custom date edit widget."""
        super().__init__(parent)

    def keyPressEvent(self, keyEvent):
        """Adjust current date when +/- is pressed by one day."""
        incs = {QtCore.Qt.Key_Up: -1, QtCore.Qt.Key_Down: 1}
        if keyEvent.key() == QtCore.Qt.Key_Up or keyEvent.key() == QtCore.Qt.Key_Down:
            inc = incs[keyEvent.key()]
            idx = self.currentIndex()
            txt = self.currentText()
            sidx = self.findText(txt, QtCore.Qt.MatchStartsWith)
            if sidx < 0 or idx > 0:
                # already selected one of the avail texts, just advance in direction
                self.setCurrentIndex(idx + inc)
            elif self.itemText(sidx) == txt:
                # current text is already one of the texts, just advance in direction
                self.setCurrentIndex(sidx + inc)
            else:
                # jump to first match
                self.setCurrentIndex(sidx)
        else:
            super().keyPressEvent(keyEvent)


class DescriptionDelegate(QtWidgets.QStyledItemDelegate):
    """Provide editing functionality for description of transaction or item cell."""

    MIN_WIDTH = 100

    def createEditor(self, parent, option, index):
        """Create an editor widget suitable for editing model data at given index."""
        widget = CustomDescrComboBox(parent)
        widget.setDuplicatesEnabled(True)
        widget.setEditable(True)
        instance = self.parent().model().data(index, QtCore.Qt.EditRole)
        strings = []
        dt = datetime.timedelta(days=90)
        if isinstance(instance, Transaction):
            # get descriptions of items near current item
            fromDate = instance.date - dt
            tillDate = instance.date + dt
            fromFilter = FilterGreaterOrEqualDate(fromDate)
            tillFilter = FilterLessOrEqualDate(tillDate)
            for trn in instance.db.filterTransactions(fromFilter & tillFilter):
                descr = trn.descr
                if not descr in strings:
                    strings += [descr]
        elif isinstance(instance, Item):
            # get descriptions of items neat current item
            fromDate = instance.transaction.date - dt
            tillDate = instance.transaction.date + dt
            fromFilter = FilterGreaterOrEqualDate(fromDate)
            tillFilter = FilterLessOrEqualDate(tillDate)
            for item in instance.db.filterItems(fromFilter & tillFilter):
                descr = item.descr
                if descr and not descr in strings:
                    strings += [descr]
        strings.sort(key=lambda x: x.lower())
        widget.addItems(strings)
        widget.insertItem(0, instance.descr)
        widget.insertSeparator(1)
        widget.setCurrentIndex(0)
        return widget

    def setModelData(self, editor, model, index):
        """Apply data from editor to model."""
        descr = editor.currentText()
        model.setData(index, descr)

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)
        if s.width() < DescriptionDelegate.MIN_WIDTH:
            s.setWidth(DescriptionDelegate.MIN_WIDTH)
        return s


class ValueDelegate(QtWidgets.QStyledItemDelegate):
    """Provide editing functionality for asset/debit of item cell."""

    MIN_WIDTH = 80

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)
        if s.width() < ValueDelegate.MIN_WIDTH:
            s.setWidth(ValueDelegate.MIN_WIDTH)
        return s

    def setModelData(self, editor, model, index):
        """Apply data from editor to model."""
        try:
            txt = editor.text()
            model.setData(index, txt)
        except:
            LOGGER.exception("Failed to apply asset/debit value: {}".format(txt))
