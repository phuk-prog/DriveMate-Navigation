"""Original bounded weekly clock evaluator. No holiday/weather inference.

Compile an entire UTC interval into conservative static legality. A route must
remain within that interval; this is not an earliest-arrival time-dependent router.
"""
from datetime import datetime, timedelta, timezone
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DAYS=('Mo','Tu','We','Th','Fr','Sa','Su')
RULES={'no_right_turn','no_left_turn','no_u_turn','no_straight_on','no_entry','no_exit',
       'only_right_turn','only_left_turn','only_u_turn','only_straight_on'}

def validate_window(window,timezone_name):
    if window is None or not timezone_name:
        raise ValueError('Conditional rules require an explicit UTC interval and IANA timezone')
    if len(window)!=2 or any(not isinstance(t,datetime) or t.utcoffset() is None for t in window):
        raise ValueError('Window needs two timezone-aware datetimes')
    a,b=(t.astimezone(timezone.utc) for t in window)
    if not a<b or b-a>timedelta(days=7):raise ValueError('Window must be positive and at most seven days')
    try:zone=ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError,ValueError,TypeError) as e:raise ValueError('Unknown IANA timezone') from e
    return (a,b),zone

def _minute(raw,end=False):
    h,m=map(int,raw.split(':'))
    if not 0<=h<=23 or not 0<=m<=59:
        if not (end and h==24 and m==0):raise ValueError('Invalid time')
    return h*60+m

def parse_schedule(raw):
    match=re.fullmatch(r'(?:(Mo|Tu|We|Th|Fr|Sa|Su)(?:-(Mo|Tu|We|Th|Fr|Sa|Su))?\s+)?(\d{2}:\d{2})-(\d{2}:\d{2})',raw.strip())
    if not match:raise ValueError('Unsupported conditional schedule')
    first,last,start,end=match.groups()
    if first:
        a=DAYS.index(first);b=DAYS.index(last or first)
        days=frozenset((a+i)%7 for i in range((b-a)%7+1))
    else:days=frozenset(range(7))
    a,b=_minute(start),_minute(end,True)
    if a==b:raise ValueError('Ambiguous equal start and end')
    return days,a,b

def active(schedule,local):
    days,a,b=schedule
    t=local.hour*60+local.minute
    if a<b:return local.weekday() in days and a<=t<b
    # Early hours belong to the previous named day's overnight interval.
    return (local.weekday() in days and t>=a) or ((local.weekday()-1)%7 in days and t<b)

def restriction_values(base,conditional,window,zone):
    if base and base not in RULES:raise ValueError('Unsupported restriction value')
    clauses=[]
    for clause in conditional.split(';'):
        m=re.fullmatch(r'\s*([a-z_]+)\s*@\s*(?:\(([^()]*)\)|([^()]*))\s*',clause)
        if not m or m[1] not in RULES:raise ValueError('Unsupported conditional restriction')
        clauses.append((m[1],parse_schedule(m[2] if m[2] is not None else m[3])))
    if len(clauses)>16:raise ValueError('Too many conditional clauses')
    a,b=window
    seen=set()
    t=a
    while t<b:
        matches={value for value,schedule in clauses if active(schedule,t.astimezone(zone))}
        # Conflicting overlapping values need review, never guess precedence.
        if len(matches)>1:raise ValueError('Conflicting overlapping conditional restrictions')
        value=next(iter(matches),base)
        if value:seen.add(value)
        t=t.replace(second=0,microsecond=0)+timedelta(minutes=1)
    return seen
