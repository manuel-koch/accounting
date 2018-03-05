# -*- coding: utf-8 -*-
'''
Functionality to apply combined filter(s) to object.

@author: Manuel Koch
'''
import abc
import enum


class Filter(abc.ABC):
    """Class to build filter for objects"""

    class Operator(enum.Enum):
        AND = 1
        OR = 2

    def __init__(self, op=None, *combineFilters):
        """Generic class to filter to be applied on objects"""
        assert op is None or isinstance(op, Filter.Operator)
        self._op = op
        self._combined = combineFilters

    def __repr__(self):
        combined = [repr(c) for c in self._combined]
        return "Filter(op={!r}{}{})".format(self._op, "," if combined else "", ",".join(combined))

    def accepted(self, obj):
        """Return true when given object is accepted by this filter instance"""
        if self._op and self._combined:
            f = self._combined[0]
            accepted = f.accepted(obj)
            for f in self._combined[1:]:
                if self._op == Filter.Operator.AND and not accepted:
                    return False
                elif self._op == Filter.Operator.OR and accepted:
                    return True
                accepted = f.accepted(obj)
            return accepted
        else:
            return self._accepted(obj)

    def rejected(self, obj):
        """Return true when given object is rejected by this filter instance"""
        if self._op and self._combined:
            f = self._combined[0]
            rejected = f.rejected(obj)
            for f in self._combined[1:]:
                if self._op == Filter.Operator.AND and rejected:
                    return True
                elif self._op == Filter.Operator.OR and not rejected:
                    return False
                rejected = f.rejected(obj)
            return rejected
        else:
            return not self._accepted(obj)

    @abc.abstractmethod
    def _accepted(self, obj):
        """Derived classes implement this method to return true when given object is filtered / accepted"""

    def __and__(self, other):
        """Returns AND combined filter of this and other filter"""
        if not isinstance(other, Filter):
            raise TypeError("Expected Filter")
        return CombinedFilter(Filter.Operator.AND, self, other)

    def __or__(self, other):
        """Returns OR combined filter of this and other filter"""
        if not isinstance(other, Filter):
            raise TypeError("Expected Filter")
        return CombinedFilter(Filter.Operator.OR, self, other)


class CombinedFilter(Filter):
    def _accepted(self, obj):
        return True
