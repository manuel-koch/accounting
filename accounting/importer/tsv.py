# -*- coding: utf-8 -*-
'''
Derived class to provide import from tab-separated-values formatted file.

@author: Manuel Koch
'''
import os
import logging

LOGGER = logging.getLogger(__name__)


class CharSepararedValues(object):

    def __init__(self, separator, inputFileObj):
        """Use given separator when reading rows"""
        self._separator = separator
        self._input = inputFileObj

    def _readrow(self):
        """Yield rows from given file like object"""
        self._input.seek(0, os.SEEK_SET)
        while True:
            line = self._input.readline()
            if not line:
                break
            line = line.strip()
            fields = [u""]
            quotes = []
            for char in line:
                inQuote = bool(len(quotes) % 2)
                if inQuote and char in quotes[-1]:
                    quotes.pop()
                elif not inQuote and char in ('"', "'"):
                    quotes += [char]
                elif char == self._separator:
                    fields += [""]
                else:
                    fields[-1] += char

            def unqoute(txt):
                if (txt.startswith(u"'") and txt.endswith(u"'")) or (txt.startswith(u'"') and txt.endswith(u'"')):
                    return txt[1:-1].strip()
                return txt.strip()

            yield [unqoute(f.strip()) for f in fields]

    def __iter__(self):
        return self._readrow()
