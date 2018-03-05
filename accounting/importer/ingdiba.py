# -*- coding: utf-8 -*-
'''
Derived importer class to import entries from
    ING Diba Bank
file.
'''
import codecs
import logging
from io import StringIO

from accounting.importer.base import ImporterBase, ImporterEntry
from accounting.importer.tsv import CharSepararedValues

LOGGER = logging.getLogger(__name__)


class ImporterIngDiba(ImporterBase):
    class Meta:
        descr = u"Import entries from tab or semicolon separated values ING DiBa Bank"
        example = u""""Buchung";"Valuta";"Auftraggeber/Empfänger";"Buchungstext";"Verwendungszweck";"Betrag";"Währung";"Saldo";"Währung"
"01.06.2015";"01.06.2015";"Mustermann,Max";"Lastschrifteinzug";"Spareinzahlung  ";"125,00";"EUR";"6.000,00";"EUR"
"04.05.2015";"04.05.2015";"Mustermann,Max";"Lastschrifteinzug";"Spareinzahlung  ";"50,00";"EUR";"6.050,00";"EUR"
"""

    def __init__(self, inputFileObj):
        """Construct importer instance for given tab-separated-values format file like object."""
        readerClass = codecs.getreader("Latin-1")
        reader = readerClass(inputFileObj)
        strFileObj = StringIO(reader.read())
        self._rows = self._readRowsWithGuessedSeparator(strFileObj)
        self._dateField = 0
        self._descrField = 4
        self._valueField = 5
        self._valueLocale = "de"
        super().__init__(strFileObj)

    def _readRowsWithGuessedSeparator(self, inputFileObj):
        rows = []
        cols = 0
        for sep in (";", "\t"):
            sepRows = list(CharSepararedValues(sep, inputFileObj))
            sepCols = sum([len(r) for r in sepRows])
            if sepCols > cols:
                rows = sepRows
                cols = sepCols
        return rows

    def entries(self):
        """Returns iterator of import entries build from current input."""
        maxFieldIndex = max(self._dateField, self._descrField, self._valueField)
        firstEntry = True
        for row in self._rows:
            if len(row) <= maxFieldIndex:
                continue

            def field(idx):
                if idx >= 0 and idx < len(row):
                    return row[idx]
                return u""

            try:
                date = ImporterEntry.date_from_string(field(self._dateField))
                descr = field(self._descrField)
                value = ImporterEntry.decimal_from_string(field(self._valueField), self._valueLocale)
                entry = ImporterEntry(date, descr, value)
                if entry.date and entry.value:
                    LOGGER.debug("Import found entry: %s" % entry)
                    if not firstEntry:
                        yield entry
                    firstEntry = False
            except:
                LOGGER.exception(u"Import for line failed: %s", row)
                pass
