# -*- coding: utf-8 -*-
'''
View to display report of account(s)

@author: Manuel Koch
'''

import os
import datetime
import logging
import urllib
import webbrowser

from PyQt5 import QtPrintSupport, QtWidgets, QtCore  # , QtWebKitWidgets

from accounting.core.dateutils import rangeDateFromTillByInterval, INTERVAL_MONTHLY
from accounting.report import Report, ReportTemplate

LOGGER = logging.getLogger(__name__)


# class MyPage(QtWebKitWidgets.QWebPage):
#
#    def __init__(self,parent=None):
#        super().__init__(parent)
#
#    def javaScriptConsoleMessage(self,msgLevel,message,lineNumber,sourceID):
#        sourceID = urllib.unquote(sourceID)
#        if sourceID.startswith("data:text/html;"):
#            sourceID = "HTML"
#        logFunc = LOGGER.info
#        if msgLevel == QtWebEngineWidgets.QWebEnginePage.WarningMessageLevel:
#            logFunc = LOGGER.warning
#        elif msgLevel == QtWebEngineWidgets.QWebEnginePage.ErrorMessageLevel:
#            logFunc = LOGGER.error
#        logFunc("Javascript Console: %s(%d): %s"%(sourceID,lineNumber,message))


class AccountReport(QtWidgets.QWidget):

    def __init__(self, accounts):
        """Construct view for given template to show account(s) report."""
        super().__init__()

        self._template = None

        today = datetime.date.today()
        startofmonth, endofmonth = rangeDateFromTillByInterval(today, today, INTERVAL_MONTHLY)
        self._report = Report(accounts[0].db, startofmonth, endofmonth)
        for acc in accounts:
            self._report += acc

        hbox = QtWidgets.QHBoxLayout()
        hbox.setContentsMargins(0, 0, 0, 0)

        vbox = QtWidgets.QVBoxLayout()
        vbox.setSpacing(4)
        vbox.setContentsMargins(0, 0, 0, 0)
        hbox.addLayout(vbox)

        hbox2 = QtWidgets.QHBoxLayout()
        hbox2.setContentsMargins(4, 0, 4, 4)
        self._fromDate = QtWidgets.QDateEdit()
        self._fromDate.setCalendarPopup(True)
        self._fromDate.setDate(startofmonth)
        self._fromDate.dateChanged.connect(self._rangeChanged)
        hbox2.addWidget(QtWidgets.QLabel("From"), alignment=QtCore.Qt.AlignRight)
        hbox2.addWidget(self._fromDate)
        hbox2.addSpacing(40)
        hbox2.addWidget(QtWidgets.QLabel("to"), alignment=QtCore.Qt.AlignRight)
        self._tillDate = QtWidgets.QDateEdit()
        self._tillDate.setCalendarPopup(True)
        self._tillDate.setDate(endofmonth)
        self._tillDate.dateChanged.connect(self._rangeChanged)
        hbox2.addWidget(self._tillDate)
        hbox2.addSpacing(40)
        self._selectBtn = QtWidgets.QPushButton("Select")
        self._selectBtn.clicked.connect(self.selectTemplate)
        hbox2.addWidget(self._selectBtn, 1)
        self._createBtn = QtWidgets.QPushButton("Create")
        self._createBtn.clicked.connect(self.refreshReport)
        hbox2.addWidget(self._createBtn, 1)
        # self._printBtn = QtWidgets.QPushButton("Print")
        # self._printBtn.clicked.connect(self.printReport)
        # hbox2.addWidget(self._printBtn, 1)

        vbox.addLayout(hbox2)

        # self._browser = QtWebKitWidgets.QWebView(self)
        # vbox.addWidget(self._browser)

        self.setLayout(hbox)

    def _rangeChanged(self):
        """Handle change of from/till date range"""
        fd = self._fromDate.date()
        fd = datetime.date(fd.year(), fd.month(), fd.day())
        td = self._tillDate.date()
        td = datetime.date(td.year(), td.month(), td.day())
        valid = fd < td
        self._createBtn.setEnabled(valid)

    def getReport(self):
        return self._report

    def selectTemplate(self):
        """Choose template file to use for report"""
        settings = QtCore.QSettings()
        settings.beginGroup("Reports")
        templatedir = settings.value("mostRecentReportDir", "")
        templatepath, dummyFilter = QtWidgets.QFileDialog.getOpenFileName(self, self.tr("Open report template..."),
                                                                          templatedir,
                                                                          self.tr("Accounting Report Files (*.accrep)"))
        if not templatepath:
            return
        templatedir = os.path.dirname(templatepath)
        settings.setValue("mostRecentReportDir", templatedir)
        settings.endGroup()

        self._template = ReportTemplate(templatedir, os.path.basename(templatepath))
        self.refreshReport()

    def refreshReport(self):
        """Handle refreshing of report rendering."""
        fd = self._fromDate.date()
        fd = datetime.date(fd.year(), fd.month(), fd.day())
        td = self._tillDate.date()
        td = datetime.date(td.year(), td.month(), td.day())
        self._report.setRange(fd, td)
        html = self._template.render(self._report)
        outname = "{}_{}_{}.html".format(fd, td, os.path.splitext(self._template.name)[0])
        outpath = os.path.join(self._template.basepath, outname)
        with open(outpath, "w+", encoding="utf-8") as f:
            f.write(html)
        url = QtCore.QUrl.fromLocalFile(outpath).toString()
        webbrowser.open(url, new=0, autoraise=True)

#    def printReport(self):
#        dialog = QtPrintSupport.QPrintPreviewDialog()
#        dialog.paintRequested.connect(self._browser.print_)
#        dialog.exec_()
