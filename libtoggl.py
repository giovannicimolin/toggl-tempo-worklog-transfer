import re
from datetime import datetime, timedelta, timezone

from toggl.TogglPy import Endpoints, Toggl
from const import TIMELOG


DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S+00:00"
ISSUE_REGEX = r"[A-Z]{2,7}-\d{1,6}"
TOGGL_API_BASE_URL = "https://www.toggl.com/api/v8/"
TOGGL_TIMELOGS_URL = TOGGL_API_BASE_URL + "time_entries"

class TogglTimesheets:
    def __init__(self, api_key):
        # create a Toggl object and set our API key
        self.toggl = Toggl()
        self.toggl.setAPIKey(api_key)

    def _get_raw_timelogs(self, start_date=None, end_date=None):
        # Add filters
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        # Make request and return
        return self.toggl.request(
            Endpoints.TIME_ENTRIES,
            parameters=params
        )

    def _get_raw_timelogs_last_n_days(self, n_days):
        last_n_days = datetime.utcnow() - timedelta(days=n_days)
        last_n_days_str = last_n_days.replace(microsecond=0, tzinfo=timezone.utc).isoformat()
        return self._get_raw_timelogs(start_date=last_n_days_str)

    @staticmethod
    def _parse_timelog(raw):
        """
        {
            'start': '2019-05-11T12:19:39+00:00',
            'stop': '2019-05-11T12:40:27+00:00',
            'description': 'Trying to deploy mongodb',
            'tags': ['BB-1212'],
            'duronly': False,
        }
        """
        if raw.get('duronly', False):
            print(raw)
            raise "Error, timelog with duronly = true"

        tags = raw['tags']
        ticket = None
        dd = False
        ff = False
        for tag in tags:
            if re.match(ISSUE_REGEX, tag):
                ticket = tag
            elif tag == 'DD':
                dd = True
            elif tag == 'FF':
                ff = True

        start = datetime.strptime(raw['start'], DATETIME_FORMAT)
        end = datetime.strptime(raw['stop'], DATETIME_FORMAT)

        return TIMELOG(
            ticket=ticket,
            date=start,
            time=end-start,
            description=raw['description'],
            ff_time=ff,
            dd_time=dd
        )

    def get_timelogs_last_n_days(self, n_days=1):
        raw_logs = self._get_raw_timelogs_last_n_days(n_days)

        result = {
            'complete': list(),
            'incomplete': list(),
        }
        for item in raw_logs:
            timelog = self._parse_timelog(item)
            if timelog.ticket:
                result['complete'].append(timelog)
            else:
                result['incomplete'].append(timelog)

        return result

    def get_timelogs(self, start_date, end_date):
        start_date_str = start_date.replace(microsecond=0, tzinfo=timezone.utc).isoformat()
        end_date_str = end_date.replace(microsecond=0, tzinfo=timezone.utc).isoformat()

        raw_logs = self._get_raw_timelogs(start_date=start_date_str, end_date=end_date_str)

        result = {
            'complete': list(),
            'incomplete': list(),
        }
        for item in raw_logs:
            timelog = self._parse_timelog(item)
            if timelog.ticket:
                result['complete'].append(timelog)
            else:
                result['incomplete'].append(timelog)

        return result
