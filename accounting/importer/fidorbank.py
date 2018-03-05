# -*- coding: utf-8 -*-
'''
Derived importer class to import entries from
    Fidor Bank
file.
'''
import codecs
import logging
from io import StringIO

from accounting.importer.base import ImporterBase, ImporterEntry
from accounting.importer.tsv import CharSepararedValues

LOGGER = logging.getLogger(__name__)


class ImporterFidorBank(ImporterBase):
    class Meta:
        descr = u"Import entries from tab or semicolon separated values Fidor Bank"
        example = u"""Datum;Beschreibung;Beschreibung2;Wert
30.11.2017;\"\"\"Freunden Geld senden\"\" an Benutzer FooBar: xxxyyy";"";-2,50
30.11.2017;Überweisung: Hello World;Empfänger: Hans Wurst, IBAN: DE84600123000045678912;-5,25
30.11.2017;Gutschrift Peter Lustig IBAN: DE765064560000023409876 BIC: GENODEF3S15 Haushalt;Absender: Marie Muster, IBAN: DE44308465000006472439, BIC: GENODEF6S48;23,67
"""

    def __init__(self, inputFileObj):
        """Construct importer instance for given tab-separated-values format file like object."""
        readerClass = codecs.getreader("Latin-1")
        reader = readerClass(inputFileObj)
        strFileObj = StringIO(reader.read())
        self._rows = self._readRowsWithGuessedSeparator(strFileObj)
        self._dateField = 0
        self._descrField = (1, 2)
        self._valueField = 3
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
        maxFieldIndex = max(self._dateField, self._descrField[0], self._descrField[1], self._valueField)
        for row in self._rows:
            if len(row) <= maxFieldIndex:
                continue

            def field(idx):
                if isinstance(idx, tuple):
                    return u"  ".join([field(i) for i in idx]).strip()
                if 0 <= idx < len(row):
                    return row[idx]
                return u""

            try:
                date = ImporterEntry.date_from_string(field(self._dateField))
                descr = field(self._descrField)
                value = ImporterEntry.decimal_from_string(field(self._valueField), self._valueLocale)
                entry = ImporterEntry(date, descr, value)
                if entry.date and entry.value:
                    LOGGER.debug("Import found entry: %s" % entry)
                    yield entry
            except:
                LOGGER.exception(u"Import for line failed: %s", row)
