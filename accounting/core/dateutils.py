# -*- coding: utf-8 -*-
'''
Helper functions related to date/time

@author: Manuel Koch
'''
import datetime
from calendar import Calendar


def date_from_value(val):
    if isinstance(val, datetime.datetime):
        return val.date()
    if isinstance(val, datetime.date):
        return val
    if isinstance(val, str):
        dt = [int(x) for x in val.split("-")]
        assert len(dt) >= 3
        return datetime.date(year=dt[0], month=dt[1], day=dt[2])
    raise TypeError("Don't know how to get date from {!r}".format(val))


def startofweek(dt):
    """Return first date of week selected by given date / datetime."""
    dt = date_from_value(dt)
    w = dt.isocalendar()[1]
    for d in Calendar().itermonthdates(dt.year, dt.month):
        if d.isocalendar()[1] == w:
            break
    return d


def endofweek(dt):
    """Return last date of month selected by given date / datetime."""
    dt = date_from_value(dt)
    wd = None
    w = dt.isocalendar()[1]
    for d in Calendar().itermonthdates(dt.year, dt.month):
        if d.isocalendar()[1] == w:
            wd = d
    return wd


def startofmonth(dt):
    """Return first date of month selected by given date / datetime."""
    dt = date_from_value(dt)
    for d in Calendar().itermonthdates(dt.year, dt.month):
        if d.month == dt.month:
            break
    return d


def endofmonth(dt):
    """Return last date of month selected by given date / datetime."""
    dt = date_from_value(dt)
    md = None
    for d in Calendar().itermonthdates(dt.year, dt.month):
        if d.month == dt.month:
            md = d
    return md


def startofyear(dt):
    """Return first date of year selected by given date / datetime."""
    dt = date_from_value(dt)
    return datetime.date(year=dt.year, month=1, day=1)


def endofyear(dt):
    """Return last date of month selected by given date / datetime."""
    dt = date_from_value(dt)
    return datetime.date(year=dt.year, month=12, day=31)


INTERVAL_DAILY = 1
INTERVAL_WEEKLY = 2
INTERVAL_MONTHLY = 3
INTERVAL_ANUALY = 4
ALL_INTERVALS = [INTERVAL_DAILY, INTERVAL_WEEKLY, INTERVAL_MONTHLY, INTERVAL_ANUALY]


def rangeDateFromTillByInterval(fromDate, tillDate, interval):
    """Adjust given from/till date by selected interval.
    Returns tuple of adjusted from/till date."""
    if interval == INTERVAL_DAILY:
        return (fromDate, tillDate)
    elif interval == INTERVAL_WEEKLY:
        return (startofweek(fromDate), endofweek(tillDate))
    elif interval == INTERVAL_MONTHLY:
        return (startofmonth(fromDate), endofmonth(tillDate))
    elif interval == INTERVAL_ANUALY:
        return (startofyear(fromDate), endofyear(tillDate))
    else:
        raise TypeError()


def getIntervalSteps(fromDate, tillDate, interval):
    fromDate, tillDate = rangeDateFromTillByInterval(fromDate, tillDate, interval)
    if interval == INTERVAL_DAILY:
        inc = lambda d: d + datetime.timedelta(days=1)
    elif interval == INTERVAL_WEEKLY:
        inc = lambda d: d + datetime.timedelta(days=7)
    elif interval == INTERVAL_MONTHLY:
        inc = lambda d: (d + datetime.timedelta(days=32)).replace(day=1)
    elif interval == INTERVAL_ANUALY:
        inc = lambda d: (d + datetime.timedelta(days=366)).replace(month=1, day=1)
    else:
        raise TypeError()
    d = fromDate
    while d < tillDate:
        yield d
        d = inc(d)


def getIntervalDescr(fromDate, tillDate, interval):
    if interval == INTERVAL_DAILY:
        return fromDate.strftime("%Y-%m-%d")
    elif interval == INTERVAL_WEEKLY:
        return fromDate.strftime("wk%U %y")
    elif interval == INTERVAL_MONTHLY:
        return fromDate.strftime("%b %y")
    elif interval == INTERVAL_ANUALY:
        return fromDate.strftime("%Y")
    else:
        raise TypeError()
