# -*- coding: utf-8 -*-
'''
View of account's transactions

@author: Manuel Koch
'''
import os
from io import StringIO
import logging

from PyQt5 import QtGui, QtWidgets, QtCore

from accounting.importer.fidorbank import ImporterFidorBank
from accounting.importer.ingdiba import ImporterIngDiba
from accounting.importer.pod import ImporterPlainOldTextDe
from accounting.importer.spardabank import ImporterSpardaBank
from accounting.gui.models import ImporterEntriesModel

LOGGER = logging.getLogger(__name__)


class InputWizardPage(QtWidgets.QWizardPage):

    def __init__(self):
        "Construct page to select source of input"
        super().__init__()
        self._dir = ""

        self.setTitle("Import from file")
        self.setSubTitle("""Please select file from which you want to import transactions.
Or paste your data into the text field.""")

        fileLabel = QtWidgets.QLabel("File:")
        self._fileEdit = QtWidgets.QLineEdit()
        fileLabel.setBuddy(self._fileEdit)
        fileBtn = QtWidgets.QPushButton("...")
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self._fileEdit, 1)
        hbox.addWidget(fileBtn)

        txtLabel = QtWidgets.QLabel("Text:")
        self._textEdit = QtWidgets.QTextEdit()
        self._textEdit.setMinimumHeight(50)
        txtLabel.setBuddy(self._textEdit)

        form = QtWidgets.QFormLayout()
        form.addRow(fileLabel, hbox)
        form.addRow(txtLabel, self._textEdit)
        self.setLayout(form)

        def onFile():
            path, dummyFilter = QtWidgets.QFileDialog.getOpenFileName(self,
                                                                      caption=self.tr("Open file for importing..."),
                                                                      directory=self._dir,
                                                                      filter=self.tr("Any File (*.*)"))
            self._fileEdit.setText(path)
            self.completeChanged.emit()

        fileBtn.pressed.connect(onFile)

        self._textEdit.textChanged.connect(self.completeChanged)

    def initializePage(self):
        "Reset values when initializing page"
        self._fileEdit.clear()
        self._textEdit.clear()

    def isComplete(self):
        "Return whether input of page is complete"
        completed = bool(self._fileEdit.text().strip()) or bool(self._textEdit.toPlainText().strip())
        return completed

    def setDefaultDir(self, defDir):
        "Set default directory to start selecting input file."
        if os.path.isdir(defDir):
            self._dir = defDir
        else:
            self._dir = ""

    def getPath(self):
        "Return path selected by user, may be empty if user pasted text instead"
        return self._fileEdit.text().strip()

    def getFile(self):
        "Returns file like object selected by user for import"
        path = self._fileEdit.text().strip()
        txt = self._textEdit.toPlainText().strip()
        if path:
            LOGGER.debug("Importing from %s..." % path)
            return open(path, "rb")
        else:
            LOGGER.debug("Importing from text...")
            return StringIO(txt)


class FormatWizardPage(QtWidgets.QWizardPage):

    def __init__(self, importers):
        "Construct page to select format of input"
        super().__init__()
        self._importers = importers
        self.setTitle("Select file format")
        self.setSubTitle("Please select which format to use to import transactions.")

        vbox = QtWidgets.QVBoxLayout()
        self._radiogrp = QtWidgets.QButtonGroup()
        for idx, c in enumerate(self._importers):
            cb = QtWidgets.QRadioButton(c.Meta.descr)
            cb.setToolTip(u"<b>Example text:</b><br/>" + "<br/>".join(
                [u"<div style='margin:0px;padding:0px;'>%s</div>" % l for l in c.Meta.example.split("\n")]))
            vbox.addWidget(cb)
            self._radiogrp.addButton(cb, idx)
        self.setLayout(vbox)

        self._radiogrp.buttonClicked.connect(self.completeChanged)

    def isComplete(self):
        "Return whether input of page is complete"
        return self._radiogrp.checkedId() >= 0

    def getImporter(self):
        "Returns ImporterBase class selected by user for import"
        return self._importers[self._radiogrp.checkedId()]


class TransactionImportWizard(QtWidgets.QWizard):

    def __init__(self):
        "Construct wizard to prepare importing of transactions for account."
        super().__init__()
        self.setWindowTitle("Transactions Import")
        self._findImporters()
        self._inputPage = InputWizardPage()
        self.addPage(self._inputPage)
        self._fmtPage = FormatWizardPage(self._importClasses)
        self.addPage(self._fmtPage)
        self.loadSettings()

    def accept(self):
        super().accept()
        self.saveSettings()

    def saveSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("ImportWizard")
        settings.setValue("recentImportDir", os.path.dirname(self._inputPage.getPath()))
        settings.endGroup()

    def loadSettings(self):
        settings = QtCore.QSettings()
        settings.beginGroup("ImportWizard")
        self._inputPage.setDefaultDir(settings.value("recentImportDir", ""))
        settings.endGroup()

    def _findImporters(self):
        "Find importer classes"
        self._importClasses = (ImporterPlainOldTextDe, ImporterSpardaBank, ImporterIngDiba, ImporterFidorBank)

    def getImporterEntriesModel(self):
        "Return instance of ImporterEntriesModel"
        progress = QtWidgets.QProgressDialog(self)
        progress.setWindowTitle("Importing...")
        progress.setRange(0, 4)
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setValue(0)
        fileObj = self._inputPage.getFile()
        LOGGER.debug("Building import entries model from %s" % repr(fileObj))
        importer = self._fmtPage.getImporter()(fileObj)
        progress.setValue(1)
        entries = list(importer.entries())
        LOGGER.debug("Found %d entries for import" % len(entries))
        progress.setValue(2)
        entries.sort(key=lambda e: e.date)
        progress.setValue(3)
        model = ImporterEntriesModel(entries)
        progress.reset()
        return model
