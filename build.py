import datetime as dt
import json
import urllib.request
from pathlib import Path

BASE = 'https://dcsd.api.nutrislice.com/menu/api/weeks/school/clear-sky/menu-type/{meal}/{y}/{m:02d}/{d:02d}/'
OUT = Path('docs/clear-sky-meals.ics')
MEAL_TYPES = ('breakfast', 'lunch')


def fetch(meal, date):
    url = BASE.format(meal=meal, y=date.year, m=date.month, d=date.day)
    req = urllib.request.Request(url, headers={'User-Agent': 'ClearSkySchoolMealsCalendar/1.0'})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def items(day):
    result = []
    for item in day.get('menu_items', []):
        food = item.get('food') or {}
        name = food.get('name') or item.get('name')
        if name and name not in result:
            result.append(name)
    return result


def escape(value):
    return str(value).replace('\\', '\\\\').replace('\n', '\\n').replace(',', '\\,').replace(';', '\\;')


def previous_meals(path):
    """Recover individual meal descriptions from the previously published ICS.

    Store the escaped text as-is, avoiding accidental changes to food names.
    """
    if not path.exists():
        return {}
    content = path.read_text(encoding='utf-8-sig')
    # Unfold RFC 5545 continuation lines, if present.
    logical_lines = content.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    unfolded = []
    for line in logical_lines:
        if line.startswith((' ', '\t')) and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    recovered = {}
    event = None
    for line in unfolded:
        if line == 'BEGIN:VEVENT':
            event = {}
        elif line == 'END:VEVENT' and event is not None:
            date = event.get('date')
            if date and event.get('description'):
                parts = event['description'].split('\\n\\n')
                for part in parts:
                    for meal in MEAL_TYPES:
                        prefix = meal.title() + ': '
                        if part.startswith(prefix):
                            recovered.setdefault(date, {})[meal] = part[len(prefix):]
            event = None
        elif event is not None:
            if line.startswith('DTSTART;VALUE=DATE:'):
                try:
                    event['date'] = dt.datetime.strptime(line.split(':', 1)[1], '%Y%m%d').date().isoformat()
                except ValueError:
                    pass
            elif line.startswith('DESCRIPTION:'):
                event['description'] = line[len('DESCRIPTION:'):]
    return recovered


def main():
    today = dt.date.today()
    start = today - dt.timedelta(days=today.weekday())
    end = start + dt.timedelta(weeks=12)
    old = previous_meals(OUT)
    # Keep old data inside the current rolling window until replacement arrives.
    meals = {
        date: data.copy()
        for date, data in old.items()
        if start <= dt.date.fromisoformat(date) < end
    }
    successes = 0
    replacements = 0
    for week in range(12):
        date = start + dt.timedelta(days=7 * week)
        for meal in MEAL_TYPES:
            try:
                data = fetch(meal, date)
                if not isinstance(data, dict) or not isinstance(data.get('days'), list):
                    raise ValueError('Invalid menu response: missing days list')
                successes += 1
            except Exception as exc:
                print(f'Fetch failed {date} {meal}; retaining previous entries: {exc}')
                continue
            for day in data['days']:
                day_date = str(day.get('date', ''))[:10]
                try:
                    day_obj = dt.date.fromisoformat(day_date)
                except ValueError:
                    continue
                if not start <= day_obj < end:
                    continue
                choices = items(day)
                if choices:
                    meals.setdefault(day_date, {})[meal] = escape(', '.join(choices))
                    replacements += 1
                # Missing/empty items do not erase previously retrieved menus.
    if not successes:
        raise RuntimeError('All Nutrislice requests failed; preserving previous calendar')
    if not meals:
        raise RuntimeError('No menu data available; preserving previous calendar')

    now = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Clear Sky School Meals//EN', 'CALSCALE:GREGORIAN', 'X-WR-CALNAME:Clear Sky School Meals', 'METHOD:PUBLISH']
    for date, meal_data in sorted(meals.items()):
        date_obj = dt.date.fromisoformat(date)
        if date_obj.weekday() >= 5:
            continue
        details = [meal.title() + ': ' + meal_data[meal] for meal in MEAL_TYPES if meal_data.get(meal)]
        if not details:
            continue
        lines.extend([
            'BEGIN:VEVENT',
            f'UID:clear-sky-meals-{date}@nutrislice-calendar',
            f'DTSTAMP:{now}',
            f'DTSTART;VALUE=DATE:{date_obj:%Y%m%d}',
            f'DTEND;VALUE=DATE:{date_obj + dt.timedelta(days=1):%Y%m%d}',
            'SUMMARY:Clear Sky Breakfast & Lunch',
            'DESCRIPTION:' + '\\n\\n'.join(details),
            'END:VEVENT',
        ])
    lines.append('END:VCALENDAR')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('\r\n'.join(lines) + '\r\n', encoding='utf-8')
    print(f'Wrote {OUT}: {sum(line == "BEGIN:VEVENT" for line in lines)} days, {replacements} meal updates, {len(old)} previously saved days')


if __name__ == '__main__':
    main()
