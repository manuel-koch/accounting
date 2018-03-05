# -*- coding: utf-8 -*-
'''
Various dialogs.

@author: Manuel Koch
'''
from PyQt5.QtWidgets import QDialog
from PyQt5.QtWidgets import QLabel
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtWidgets import QPushButton
from PyQt5.QtWidgets import QFormLayout, QHBoxLayout

from accounting.core.core import Account


class EditAccountDialog(QDialog):
    "Dialog to edit account properties"

    def __init__(self, account, parent=None):
        "Construct dialog to edit account"
        super().__init__(parent)
        self.setWindowTitle("Edit Account")

        self._acc = account

        self._nameTxt = QLineEdit(self._acc.name, self)
        self._typeCb = QComboBox(self)
        for idx, typeId in enumerate(Account.ALL_TYPES):
            typeName = Account.ALL_TYPES[typeId]
            self._typeCb.addItem(typeName, userData=typeId)
            if typeId == self._acc.type:
                self._typeCb.setCurrentIndex(idx)

        self._okBtn = QPushButton("Ok", self)
        self._okBtn.pressed.connect(self.accept)
        self._cancelBtn = QPushButton("Cancel", self)
        self._cancelBtn.pressed.connect(self.reject)

        form = QFormLayout()
        form.addRow(QLabel("Name"), self._nameTxt)
        form.addRow(QLabel("Type"), self._typeCb)

        hbox = QHBoxLayout()
        hbox.addWidget(self._okBtn)
        hbox.addWidget(self._cancelBtn)
        form.addRow(QLabel(""), hbox)

        self.setLayout(form)

    def accept(self):
        self._acc.setName(self._nameTxt.text())
        self._acc.setType(self._typeCb.currentData())
        return super().accept()
