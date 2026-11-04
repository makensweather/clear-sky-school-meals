import datetime as dt
import json
import os
import urllib.request
from pathlib import Path

BASE = 'https://dcsd.api.nutrislice.com/menu/api/weeks/school/clear-sky/menu-type/{meal}/{y}/{m:02d}/{d:02d}/'
OUT = Path('docs/clear-sky-meals.ics')

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

def main():
    today = dt.date.today()
    start = today - dt.timedelta(days=today.weekday())
    meals = {}
    successes = 0
    for week in range(12):
        date = start + dt.timedelta(days=7 * week)
        for meal in ('breakfast', 'lunch'):
            try:
                data = fetch(meal, date)
                successes += 1
            except Exception as exc:
                print(f'Fetch failed {date} {meal}: {exc}')
                continue
            for day in data.get('days', []):
                day_date = str(day.get('date', ''))[:10]
                if not day_date:
                    continue
                choices = items(day)
                if choices:
                    meals.setdefault(day_date, {})[meal] = choices
    if not successes or not meals:
        raise RuntimeError('No valid Nutrislice menu data; preserving previous calendar')
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Clear Sky School Meals//EN', 'CALSCALE:GREGORIAN', 'X-WR-CALNAME:Clear Sky School Meals', 'METHOD:PUBLISH']
    for date, meal_data in sorted(meals.items()):
        date_obj = dt.date.fromisoformat(date)
        if date_obj.weekday() >= 5:
            continue
        details = []
        for meal in ('breakfast', 'lunch'):
            if meal in meal_data:
                details.append(meal.title() + ': ' + ', '.join(meal_data[meal]))
        if not details:
            continue
        lines.extend(['BEGIN:VEVENT', f'UID:clear-sky-meals-{date}@nutrislice-calendar', f'DTSTAMP:{now}', f'DTSTART;VALUE=DATE:{date_obj:%Y%m%d}', f'DTEND;VALUE=DATE:{date_obj + dt.timedelta(days=1):%Y%m%d}', 'SUMMARY:Clear Sky Breakfast & Lunch', 'DESCRIPTION:' + escape('\n\n'.join(details)), 'END:VEVENT'])
    lines.append('END:VCALENDAR')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('\r\n'.join(lines) + '\r\n', encoding='utf-8')
    print(f'Wrote {OUT} with {sum(line == "BEGIN:VEVENT" for line in lines)} days')

if __name__ == '__main__':
    main()
