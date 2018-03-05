# -*- coding: utf-8 -*-
'''
Helper functions related to handling values.

@author: Manuel Koch
'''
import re
import operator
from decimal import Decimal
import unittest

ARG1 = "(?P<arg1>-?\d+([\.,]\d*)?)"
ARG2 = "(?P<arg2>-?\d+([\.,]\d*)?)"
ADD_RE = re.compile(ARG1 + "\+" + ARG2)
SUB_RE = re.compile(ARG1 + "\-" + ARG2)
MUL_RE = re.compile(ARG1 + "\*" + ARG2)
DIV_RE = re.compile(ARG1 + "\/" + ARG2)
PAR_RE = re.compile("\((?P<arg>.+)\)")

PRECISION_SAMPLES = (Decimal(1), Decimal(10) ** -1, Decimal(10) ** -2, Decimal(10) ** -3, Decimal(10) ** -4)


class ValueException(Exception):
    pass


def eval_decimal(txt, prec=2):
    """Evaluate arithmetic expression involving add, subtract, multiply and divide
    and return Decimal with given number of precision."""

    def norm(n):
        return n.replace(",", ".")

    def evalpair(a, b, op):
        a = norm(a)
        b = norm(b)
        v = op(Decimal(a), Decimal(b))
        sign = "+" if a.startswith("-") and v > 0 else ""
        return sign + str(v)

    while True:
        txt = txt.strip().replace(" ", "")
        if not txt:
            return Decimal(0)
        m = PAR_RE.search(txt)
        if m:
            v = eval_decimal(m.group("arg"), -1)
            txt = txt[:m.start()] + str(v) + txt[m.end():]
            continue
        mulMatch = MUL_RE.search(txt)
        divMatch = DIV_RE.search(txt)
        if (mulMatch and not divMatch) or (mulMatch and divMatch and mulMatch.start() < divMatch.start()):
            txt = txt[:mulMatch.start()] + evalpair(mulMatch.group("arg1"), mulMatch.group("arg2"), operator.mul) + txt[
                                                                                                                    mulMatch.end():]
            continue
        elif (divMatch and not mulMatch) or (divMatch and mulMatch and divMatch.start() < mulMatch.start()):
            txt = txt[:divMatch.start()] + evalpair(divMatch.group("arg1"), divMatch.group("arg2"), operator.div) + txt[
                                                                                                                    divMatch.end():]
            continue
        addMatch = ADD_RE.search(txt)
        subMatch = SUB_RE.search(txt)
        if (addMatch and not subMatch) or (addMatch and subMatch and addMatch.start() < subMatch.start()):
            txt = txt[:addMatch.start()] + evalpair(addMatch.group("arg1"), addMatch.group("arg2"), operator.add) + txt[
                                                                                                                    addMatch.end():]
            continue
        elif (subMatch and not addMatch) or (subMatch and addMatch and subMatch.start() < addMatch.start()):
            txt = txt[:subMatch.start()] + evalpair(subMatch.group("arg1"), subMatch.group("arg2"), operator.sub) + txt[
                                                                                                                    subMatch.end():]
            continue
        break
    d = Decimal(norm(txt))
    if prec >= 0 and prec < len(PRECISION_SAMPLES):
        return d.quantize(PRECISION_SAMPLES[prec])
    else:
        return d


def to_decimal(val, prec=2):
    """Convert given value to Decimal of selected precision"""
    if val is None:
        d = Decimal(0)
    elif isinstance(val, Decimal):
        d = val
    elif isinstance(val, int) or isinstance(val, float):
        d = Decimal(val)
    elif isinstance(val, str):
        d = eval_decimal(val, prec)
    else:
        raise TypeError()
    if prec < 0 or prec >= len(PRECISION_SAMPLES):
        raise ValueException("Invalid precision %s" % prec)
    return d.quantize(PRECISION_SAMPLES[prec])


class TestItem(unittest.TestCase):

    def test_eval(self):
        self.assertEqual(eval_decimal("1,35-0,35+0.5"), Decimal("1.50"))
        self.assertEqual(eval_decimal("-1,35-0,2/-2"), Decimal("-1.25"))
        self.assertEqual(eval_decimal("-1,35-0,2*-0.5"), Decimal("-1.25"))
        self.assertEqual(eval_decimal("2*3-3*-2"), Decimal("12"))
        self.assertEqual(eval_decimal("2*3-3*2"), Decimal("0"))
        self.assertEqual(eval_decimal("2*3+3*-2"), Decimal("0"))
        self.assertEqual(eval_decimal("1.3+1.3"), Decimal("2.6"))
        self.assertEqual(eval_decimal("1.50 + 1.50"), Decimal("3.0"))
        self.assertEqual(eval_decimal("1.50 - 1.50"), Decimal(0))
        self.assertEqual(eval_decimal("2 * 1.50"), Decimal("3.0"))
        self.assertEqual(eval_decimal("3 / 1.50"), Decimal(2))
        self.assertEqual(eval_decimal("1 + 3 / 1.50"), Decimal(3))
        self.assertEqual(eval_decimal("1 - 3 / 1.50"), Decimal(-1))
        self.assertEqual(eval_decimal("2 * ( 1 + 1 )"), Decimal(4))
        self.assertEqual(eval_decimal("2 * ( 1.3 + 1.5 )"), Decimal("5.6"))
