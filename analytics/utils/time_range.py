from datetime import datetime, timedelta
from django.utils import timezone


def parse_range(q):
    """date_from/date_to or period presets (daily/weekly/monthly/yearly/all)."""
    def parse_one(s, end=False):
        if not s:
            return None
        dt = datetime.fromisoformat(s)
        if len(s) == 10 and end:
            dt = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        return dt

    def start_of_week(dt):
        return (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

    def month_bounds(dt):
        start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            next_start = start.replace(year=start.year + 1, month=1)
        else:
            next_start = start.replace(month=start.month + 1)
        end = next_start - timedelta(microseconds=1)
        return start, end

    def year_bounds(dt):
        start = dt.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1) - timedelta(microseconds=1)
        return start, end

    tz = timezone.get_default_timezone()
    now = timezone.localtime()

    df_raw = parse_one(q.get('date_from'))
    dt_raw = parse_one(q.get('date_to'), end=True)
    period = (q.get('period') or q.get('range') or q.get('freq') or '').lower().strip()

    if df_raw or dt_raw:
        df = df_raw or now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt = dt_raw or now
    elif period in {'daily', 'day'}:
        anchor = now
        df = anchor.replace(hour=0, minute=0, second=0, microsecond=0)
        dt = anchor.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif period in {'weekly', 'week'}:
        ws = start_of_week(now)
        df, dt = ws, ws + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
    elif period in {'monthly', 'month'}:
        df, dt = month_bounds(now)
    elif period in {'yearly', 'year'}:
        df, dt = year_bounds(now)
    elif period in {'all', 'full'}:
        df, dt = datetime(1970, 1, 1), now
    else:
        df = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dt = now

    # Anchor period to date_from if provided (and no explicit range used)
    if (not (df_raw or dt_raw)) and q.get('date_from') and period in {'daily','day','weekly','week','monthly','month','yearly','year'}:
        anchor = datetime.fromisoformat(q.get('date_from'))
        if timezone.is_naive(anchor):
            anchor = timezone.make_aware(anchor, tz)
        if period in {'daily','day'}:
            df = anchor.replace(hour=0, minute=0, second=0, microsecond=0)
            dt = anchor.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period in {'weekly','week'}:
            ws = start_of_week(anchor)
            df, dt = ws, ws + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
        elif period in {'monthly','month'}:
            df, dt = month_bounds(anchor)
        elif period in {'yearly','year'}:
            df, dt = year_bounds(anchor)

    if timezone.is_naive(df):
        df = timezone.make_aware(df, tz)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, tz)
    return df, dt