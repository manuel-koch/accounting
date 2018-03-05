# -*- coding: utf-8 -*-
'''
Derived importer class to import entries from
plain text formatted file.
'''
import re

import accounting.importer.base
from accounting.importer.base import ImporterEntry


class ImporterPlainOldText(accounting.importer.base.ImporterBase):
    ITEM_RE = re.compile(r"\s*(?P<descr>.+)\s+(?P<value>-?\d+([,\.](\d+|-))?)")

    class Meta:
        descr = "Import entries from plain text file"
        example = ""

    def __init__(self, inputFileObj, valueLocaleName=""):
        """Construct importer instance for given plain text formated file."""
        super().__init__(inputFileObj)
        self._valueLocale = valueLocaleName

    def entries(self):
        """Returns iterator of entries build from current input."""
        recentDate = None
        line = "x"
        while True:
            line = self._input.readline()
            if not line:
                break
            line = line.strip()

            try:
                recentDate = ImporterEntry.date_from_string(line)
                continue
            except:
                pass
            if not recentDate:
                continue

            m = ImporterPlainOldText.ITEM_RE.match(line)
            if m:
                try:
                    date = recentDate
                    descr = m.group("descr")
                    value = m.group("value")
                    if value.endswith("-"):
                        value = value[:-1] + "0"
                    value = ImporterEntry.decimal_from_string(value, self._valueLocale)
                    entry = ImporterEntry(date, descr, value)
                    if entry.value:
                        yield entry
                except:
                    pass


class ImporterPlainOldTextDe(ImporterPlainOldText):
    class Meta:
        descr = "Import entries from plain text file (de)"
        example = """01.06.
Edeka 29,95
Eisdiele 8,-

03.06.13
Bus 2,8"""

    def __init__(self, inputFileObj):
        """Construct importer instance for given plain text formated file."""
        super().__init__(inputFileObj, "de")
