# -*- coding: utf-8 -*-
'''
Base class to provide interface of importer class for accounting package.

@author: Manuel Koch
'''
import codecs
import datetime
import locale
import babel.numbers
import babel.plural  # need this import for PyInstaller bundled application
from decimal import Decimal
import logging

from accounting.core.value import to_decimal

LOGGER = logging.getLogger(__name__)

DATE_FORMATS = ("%Y-%m-%d", "%d.%m.%Y",
                "%m-%d", "%d.%m.")


class ImportException(Exception):
    pass


class DateException(ImportException):
    pass


class ValueException(ImportException):
    pass


class ImporterEntry(object):
    """This class represent one entry that got imported from current input."""

    def __init__(self, date, descr, value):
        """Construct a new import entry."""
        if not isinstance(date, datetime.date):
            raise TypeError("Argument date must be a date")
        if not isinstance(descr, str):
            raise TypeError("Argument descr must be a string")
        if not isinstance(value, Decimal):
            raise TypeError("Argument value must be Decimal")
        self._date = date
        self._descr = descr
        self._value = value
        self._confirmed = False

    @property
    def date(self):
        return self._date

    @property
    def descr(self):
        return self._descr

    @property
    def value(self):
        return self._value

    def inverseValue(self):
        """Inverse current value"""
        self._value *= -1

    @property
    def confirmed(self):
        return self._confirmed

    def setConfirmed(self, confirmed):
        self._confirmed = confirmed

    def __repr__(self):
        return "%s %s %s" % (self._date, self._value, self._descr)

    @staticmethod
    def date_from_string(s):
        """Return date converted from given string"""
        for f in DATE_FORMATS:
            try:
                dt = datetime.datetime.strptime(s, f)
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.datetime.now().year)
                    if dt > datetime.datetime.now():
                        dt = dt.replace(year=datetime.datetime.now().year - 1)
                return dt.date()
            except:
                pass
        raise DateException("Unknown date format:" + s)

    @staticmethod
    def decimal_from_string(s, localename=""):
        """Return Decimal value converted from given string.
        Using selected named locale ( i.e. de_DE, en_US ) to parse value."""
        try:
            if not localename:
                localename = locale.getlocale()
            return to_decimal(babel.numbers.parse_decimal(s, localename))
        except:
            LOGGER.exception("Failed to convert to decimal")
            raise ValueException("Unknown value format:" + s)


class ImporterBase(object):
    """This class represent the interface that derived functionality needs to provide for importing
    entries from a file like object."""

    class Meta:
        descr = "Short description of this importer"
        example = "Example of formatted text that this importer can parse"

    def __init__(self, inputFileObj):
        """Construct importer instance for given file like object."""
        self._input = inputFileObj

    def entries(self):
        """Returns iterator of entries build from current input."""
        return iter([])
