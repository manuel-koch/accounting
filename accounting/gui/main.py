#!/usr/bin/env python2
#  -*- coding: utf-8 -*-
'''
GUI functionality of accounting package

@author: Manuel Koch
'''

__version__ = "1.1.1"

import sys
import os
import datetime
import random
import logging
import codecs

# including more than we actually need to force PyInstaller build with required packages
from PyQt5 import QtGui, QtWidgets, QtCore, QtNetwork  # , QtWebKitWidgets
from PyQt5.QtWidgets import QDialog

import accounting.gui.resources
from accounting.core.core import Database, Account, Transaction, Item
from accounting.gui.models import AccountModel
from accounting.gui.widget.acctree import AccountTree
from accounting.gui.widget.trnview import AccountTransactionView
from accounting.gui.widget.report import AccountReport
from accounting.gui.widget.dialog import EditAccountDialog

LOGGER = logging.getLogger("accounting")


class UILoggingHandler(logging.Handler):

    def __init__(self, callback):
        "Construct UI logging handler"
        super().__init__()
        self._callback = callback

    def emit(self, record):
        "Emit given record by actually logging it"
        self._callback(record.levelno, self.format(record))


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, dbPath=None):
        "Construct main window and load selected database."
        super().__init__()

        self._initLogger()

        self._queuedActions = []

        self._splash = None
        self._splashEnabled = True  # disable splash for debugging
        LOGGER.info("Starting...")

        self._dbPath = dbPath
        self._db = None
        self._recentReportDir = ""
        self._discardTabChange = False

        self.initUI()
        self._handleQueuedAction(True)

    def _initLogger(self):
        "Initialize logging"
        self._logDlg = LogDialog()

        level = logging.DEBUG
        rootLogger = logging.getLogger()
        rootLogger.setLevel(level)

        self._outLogHdl = logging.StreamHandler(sys.stdout)
        self._outLogHdl.setLevel(level)
        rootLogger.addHandler(self._outLogHdl)

        # f = os.path.expanduser("~/tmp/accounting.log")
        # self._fileLogHdl = logging.StreamHandler( codecs.getwriter(consoleEncoding)(open(f,"wb+"),"replace") )
        # self._fileLogHdl.setLevel( level )
        # rootLogger.addHandler( self._fileLogHdl )

        self._uiLogHdl = UILoggingHandler(self._logDlg.log)
        self._uiLogHdl.setLevel(level)
        rootLogger.addHandler(self._uiLogHdl)

        self._splashLogHdl = UILoggingHandler(self._splashLog)
        self._splashLogHdl.setLevel(level)
        rootLogger.addHandler(self._splashLogHdl)

        rootLogger.setLevel(level)

    def restoreSettings(self):
        "Restore previous application settings"
        screenDim = QtWidgets.QDesktopWidget().screenGeometry()
        defaultSize = QtCore.QSize(screenDim.width() * 0.75, screenDim.height() * 0.75)
        defaultPos = QtCore.QPoint((screenDim.width() / 2) - (defaultSize.width() / 2),
                                   (screenDim.height() / 2) - (defaultSize.height() / 2))
        settings = QtCore.QSettings()

        settings.beginGroup("MainWindow")

        self.resize(settings.value("size", defaultSize))
        self.move(settings.value("pos", defaultPos))

        self._recentReportDir = settings.value("mostRecentReportDir", "")

        loadDbPath = self._dbPath
        if not loadDbPath:
            loadDbPath = settings.value("mostRecentDb", "")
        if loadDbPath:
            if os.path.isfile(loadDbPath):
                self._queuedActions += [(self.menuOpenDatabase, (loadDbPath,))]
            else:
                LOGGER.warning("Skipped loading non existing database at {}".format(loadDbPath))
        self._dbPath = ""

        try:
            currTabName = ""
            for idx in range(settings.beginReadArray("recentTabs")):
                settings.setArrayIndex(idx)
                tab = settings.value("tab", "")
                tabType, tabCurr, tabName = tab.split(":")
                if tabType == "AccTrn":
                    self._queuedActions += [(self._openAccTrnView, (tabName,))]
                    if tabCurr:
                        currTabName = tabCurr
            self._queuedActions += [(self._openAccTrnView, (currTabName,))]
        except:
            LOGGER.exception("Failed to restore recent tabs")
        finally:
            settings.endArray()

        settings.endGroup()

    def saveSettings(self):
        "Save current application settings"
        settings = QtCore.QSettings()
        settings.beginGroup("MainWindow")

        settings.setValue("size", self.size())
        settings.setValue("pos", self.pos())
        settings.setValue("mostRecentDb", self._dbPath)

        recentTabIdx = 0
        settings.beginWriteArray("recentTabs")
        for tabIdx in range(self._tabs.count()):
            widget = self._tabs.widget(tabIdx)
            currWidget = self._tabs.currentWidget() == widget
            if isinstance(widget, AccountTransactionView):
                settings.setArrayIndex(recentTabIdx)
                recentTabIdx += 1
                settings.setValue("tab", "AccTrn:%s:%s" % ("*" if currWidget else "", widget.getAccount().fullname))
        settings.endArray()

        settings.endGroup()

    def closeEvent(self, closeEvt):
        "Handle event to close main window"
        if self.checkUnsavedChanges():
            self.saveSettings()
            closeEvt.accept()
        else:
            closeEvt.ignore()

    def _splashMsg(self, msg):
        "Change splash screen message"
        if not self._splash and self._splashEnabled:
            self._splash = QtWidgets.QSplashScreen(QtGui.QPixmap(":/images/splash.jpg"),
                                                   flags=QtCore.Qt.WindowStaysOnTopHint)
            self._splash.show()
        elif msg is None and self._splash:
            LOGGER.removeHandler(self._splashLogHdl)
            QtCore.QTimer.singleShot(200, lambda: self._splash.finish(self))

        if self._splash:
            if msg:
                self._splash.showMessage(msg, color=QtGui.QColor("black"))
            QtCore.QCoreApplication.processEvents()

    def _splashLog(self, level, msg):
        "Add given logging message to splash"
        for l in msg.split("\n"):
            self._splashMsg(l)

    def initUI(self):
        "Initialize UI."
        centralWidget = QtWidgets.QWidget()
        self.setCentralWidget(centralWidget)

        vbox = QtWidgets.QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)

        self._splitter = QtWidgets.QSplitter()
        self._splitter.setChildrenCollapsible(False)

        self._tabs = QtWidgets.QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.currentChanged.connect(self.handleUpdateAccTab)
        self._tabs.tabCloseRequested.connect(self.handleCloseAccTab)

        self._accountTree = AccountTree()
        self._accountTree.showAccount.connect(self._openAccTrnView)
        self._accountTree.createReport.connect(self.handleAccTreeReport)
        self._accountTree.importData.connect(self.handleAccTreeImport)
        self._accountTree.dirty.connect(self.handleModelDirty)
        self._accountTree.editAccount.connect(self.handleEditAccount)
        self._splitter.addWidget(self._accountTree)
        self._splitter.addWidget(self._tabs)
        vbox.addWidget(self._splitter)

        hbox = QtWidgets.QHBoxLayout()
        hbox.setSpacing(4)
        hbox.setContentsMargins(2, 2, 2, 2)
        hbox.addLayout(vbox, 0)

        centralWidget.setLayout(hbox)

        self.initMenuBar()
        self.initStatusBar()
        self.restoreSettings()
        if not self._db:
            self.menuNewDatabase()
        self.show()
        self.raise_()

    def initStatusBar(self):
        self.statusBar().showMessage("Ready.", 4000)

    def initMenuBar(self):
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu(self.tr("File"))
        fileMenu.addAction(self.tr("New database..."), self.menuNewDatabase)
        fileMenu.addAction(self.tr("New random database..."), self.menuNewRandomDatabase)
        fileMenu.addSeparator()
        fileMenu.addAction(self.tr("Open database..."), self.menuOpenDatabase)
        fileMenu.addSeparator()
        self._actionSave = fileMenu.addAction(self.tr("Save database..."), self.menuSaveDatabase)
        self._actionSave.setDisabled(True)
        self._actionSaveAs = fileMenu.addAction(self.tr("Save database as..."), self.menuSaveAsDatabase)
        fileMenu.addSeparator()
        fileMenu.addAction(self.tr("Quit"), self.close)

        helpMenu = menuBar.addMenu(self.tr("Help"))
        helpMenu.addAction(self.tr("About..."), self.menuAbout)
        helpMenu.addAction(self.tr("About Qt..."), self.menuAboutQt)
        helpMenu.addSeparator()
        helpMenu.addAction(self.tr("Log..."), self._logDlg.show)

    def _handleQueuedAction(self, triggerTimer=False):
        if not self._queuedActions:
            LOGGER.info("Ready...")
            self._splashMsg(None)
            return
        if triggerTimer:
            QtCore.QTimer.singleShot(100, self._handleQueuedAction)
            return
        func, args = self._queuedActions.pop(0)
        func(*args)
        self._handleQueuedAction(True)

    def checkUnsavedChanges(self):
        """Returns true when unsaved changes have been saved or user wants to discard unsaved changes.
        Returns False if there are unsaved changes and user wants to abort current action"""
        if self.isModelDirty():
            res = QtWidgets.QMessageBox.question(self, self.tr("Unsaved changes"), self.tr(
                "There are unsaved changes in current database. Do you want to save them now ?"),
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel)
            if res == QtWidgets.QMessageBox.Yes:
                self.menuSaveDatabase()
            elif res == QtWidgets.QMessageBox.Cancel or res == QtWidgets.QMessageBox.Escape:
                return False
        return True

    def _clearViews(self):
        while self._tabs.count():
            self._discardTabChange = True
            self._tabs.removeTab(0)
        self._accountTree.setDatabase(self._db)

    def menuAbout(self):
        "Show about dialog."
        QtWidgets.QMessageBox.about(self, self.tr("About Accounting"), self.tr(
            "A tool to manage transactions of accounts and generate reports of transactions.\n\nVersion " + __version__ + "\nWritten by Manuel Koch."))

    def menuAboutQt(self):
        "Show about dialog."
        QtWidgets.QMessageBox.aboutQt(self, self.tr("About Qt"))

    def menuNewDatabase(self):
        "Create a new and empty database."
        if not self.checkUnsavedChanges():
            return
        LOGGER.info("Creating new database...")
        self._clearViews()
        self._db = Database()
        self._dbPath = "unnamed"
        self._accountTree.setDatabase(self._db)
        self.statusBar().showMessage("Created empty database", 2000)

    def menuNewRandomDatabase(self):
        "Create a new and random filled database."
        LOGGER.info("Creating new random database...")
        self._clearViews()

        self._db = Database()
        self._dbPath = "unnamed"

        self._db._parsing = True
        for i in range(32):
            acc = Account("Account%d" % i)
            self._db += acc
            for ii in range(2):
                cacc = Account("Account%d" % ii)
                acc += cacc
                for iii in range(2):
                    ccacc = Account("Account%d" % iii)
                    cacc += ccacc
        accs = self._db.getChildAccounts(True)
        dt = datetime.datetime.now() - datetime.timedelta(seconds=60 * 60 * 500)
        for i in range(3000):
            t = Transaction(dt, "#" * random.randint(1, 32))
            self._db += t
            v = float(random.randint(1, 1000)) / 100
            i = Item("A" * random.randint(1, 32), v)
            t += i
            i += random.choice(accs)
            i = Item("B" * random.randint(1, 32), -v)
            t += i
            i += random.choice(accs)
            dt += datetime.timedelta(seconds=60 * 60)
        self._db._parsing = False

        self._accountTree.setDatabase(self._db)
        self._accountTree.expandAll()
        self.statusBar().showMessage("Created random database", 2000)

    def menuOpenDatabase(self, filepath=""):
        "Open existing database from file."
        if not self.checkUnsavedChanges():
            return
        if not filepath or not os.path.isfile(filepath):
            filepath, dummyFilter = QtWidgets.QFileDialog.getOpenFileName(self, self.tr("Open accounting database..."),
                                                                          "", self.tr(
                    "Accounting Database Files (*.accdb)"))
        if not filepath or not os.path.isfile(filepath):
            return
        self._clearViews()
        LOGGER.info("Loading database %s..." % filepath)
        self._db = Database.load(filepath)
        self._dbPath = filepath
        self._accountTree.setDatabase(self._db)
        self._accountTree.expandAll()
        self.statusBar().showMessage("Loaded database " + self._dbPath, 2000)
        self.handleModelDirty(False)
        LOGGER.info("Loaded database %s." % filepath)

    def _resetDirty(self):
        "Tell all models to be clean."
        self._accountTree.setDirty(False)
        for i in range(self._tabs.count()):
            widget = self._tabs.widget(i)
            if isinstance(widget, AccountTransactionView):
                widget.setDirty(False)

    def menuSaveDatabase(self):
        "Save current database to file."
        LOGGER.info("Saving database %s..." % self._dbPath)
        self._db.save(self._dbPath)
        self._resetDirty()
        self.statusBar().showMessage("Saved database " + self._dbPath, 2000)
        LOGGER.info("Saved database %s." % self._dbPath)

    def menuSaveAsDatabase(self):
        "Save current database to file."
        fileName, dummyFilter = QtWidgets.QFileDialog.getSaveFileName(self, self.tr("Save accounting database..."), "",
                                                                      self.tr("Accounting Database Files (*.accdb)"))
        if not fileName:
            return
        LOGGER.info("Saving database as %s..." % fileName)
        self._db.save(fileName)
        self._dbPath = fileName
        self._resetDirty()
        self.statusBar().showMessage("Saved database as " + self._dbPath, 2000)
        LOGGER.info("Saved database as %s..." % self._dbPath)

    def isModelDirty(self):
        "Return whether our model is dirty and needs to be saved."
        if self._accountTree.isDirty():
            return True
        for i in range(self._tabs.count()):
            widget = self._tabs.widget(i)
            if isinstance(widget, AccountTransactionView):
                if widget.isDirty():
                    return True
        return False

    def handleModelDirty(self, isDirty):
        "Handle altered model."
        if not isDirty or os.path.isfile(self._dbPath):
            self._actionSave.setEnabled(isDirty)
        if isDirty:
            self.setWindowTitle("Accounting - " + self._dbPath + " (modified)")
        else:
            self.setWindowTitle("Accounting - " + self._dbPath)

    def handleEditAccount(self, acc):
        "Handle editing account"
        dlg = EditAccountDialog(acc, self)
        if dlg.exec_() == QDialog.Accepted:
            pass

    def handleAccTreeRename(self, acc):
        "Handle renamed account to update tab header"
        for i in range(self._tabs.count()):
            widget = self._tabs.widget(i)
            if isinstance(widget, AccountTransactionView):
                if widget.getAccount() == acc:
                    self._tabs.setTabText(i, acc.fullname)
                    return

    def _openAccTrnView(self, acc):
        "Open or activate tab with transaction table view for given Account instance and return view instance."
        if isinstance(acc, str):
            if not acc in self._db:
                return
            acc = self._db[acc]
        LOGGER.info("Opening account transaction view %s" % acc.fullname)
        for i in range(self._tabs.count()):
            widget = self._tabs.widget(i)
            if isinstance(widget, AccountTransactionView):
                if widget.getAccount() == acc:
                    self.statusBar().showMessage("Selecting account transactions view for %s..." % acc.fullname, 1000)
                    self._tabs.setCurrentIndex(i)
                    return widget

        self.statusBar().showMessage("Creating account transactions view for %s..." % acc.fullname, 1000)
        accView = AccountTransactionView()
        accView.dirty.connect(self.handleModelDirty)
        accView.setAccount(acc)

        self._discardTabChange = True
        self._tabs.addTab(accView, acc.fullname)
        self._tabs.setCurrentWidget(accView)
        acc.nameChanged.connect(lambda n: self.handleAccTreeRename(acc))

        return accView

    def handleAccTreeReport(self):
        indexes = self._accountTree.selectedIndexes()
        if not indexes:
            return
        self.statusBar().showMessage("Creating report for %d accounts..." % len(indexes), 1000)
        accounts = [self._accountTree.model().data(idx, AccountModel.AccountRole) for idx in indexes]
        accReport = AccountReport(accounts)
        self._tabs.addTab(accReport, "Report")
        self._tabs.setCurrentWidget(accReport)

    def handleAccTreeImport(self):
        indexes = self._accountTree.selectedIndexes()
        if not indexes:
            return
        idx = indexes[0]
        if not idx.isValid():
            return

        acc = self._accountTree.model().data(idx, AccountModel.AccountRole)
        accView = self._openAccTrnView(acc)
        accView.startImport()

    def handleUpdateAccTab(self, idx):
        "Handle activation of another tab to force updating it's content."
        if idx >= 0 and not self._discardTabChange:
            # force updating all the table cells from model
            widget = self._tabs.currentWidget()
            if isinstance(widget, AccountTransactionView):
                widget.refreshFromModel()
        self._discardTabChange = False

    def handleCloseAccTab(self, idx):
        "Handle request to closing tab."
        self._tabs.removeTab(idx)


class LogDialog(QtWidgets.QDialog):
    COLOR_ERROR = QtGui.QColor(200, 50, 50)
    COLOR_WARNING = QtGui.QColor(255, 220, 0)

    def __init__(self, parent=None):
        "Construct the log dialog"
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self._text = QtWidgets.QTextEdit()
        self._text.setReadOnly(True)
        self._text.setLineWrapMode(QtWidgets.QTextEdit.NoWrap)
        self._defColor = self._text.textColor()
        hbox = QtWidgets.QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)
        vbox = QtWidgets.QVBoxLayout()
        vbox.setSpacing(4)
        vbox.addWidget(QtWidgets.QLabel("Messages..."))
        vbox.addLayout(hbox)
        closeBtn = QtWidgets.QPushButton("Ok")
        closeBtn.pressed.connect(self.close)
        vbox.addWidget(closeBtn, alignment=QtCore.Qt.AlignRight)
        hbox.addWidget(self._text)
        self.setLayout(vbox)

    def show(self):
        "Show this dialog"
        super().show()
        self.raise_()

    def log(self, level, msg):
        "Handle new formated log record"
        col = self._defColor
        if level >= logging.ERROR:
            col = LogDialog.COLOR_ERROR
        elif level >= logging.WARN:
            col = LogDialog.COLOR_WARNING
        self._text.setTextColor(col)
        self._text.insertPlainText(msg + "\n")
        self._text.setTextColor(self._defColor)


def main():
    "Main entry point of application"
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName("Accounting")
    app.setOrganizationDomain("accounting.com")
    app.setApplicationName("Accounting")
    app.setApplicationVersion("1.0")

    parser = QtCore.QCommandLineParser()
    parser.setApplicationDescription("Double accounting application")
    parser.addHelpOption()
    parser.addVersionOption()

    loadDbOption = QtCore.QCommandLineOption("db", "Load selected database on startup", "PATH")
    loadDbOption.setDefaultValue("")
    parser.addOption(loadDbOption)

    parser.process(app)

    wnd = MainWindow(dbPath=parser.value(loadDbOption))

    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
