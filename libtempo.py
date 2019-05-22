import json
import requests


ENDPOINTS = {
    'login': '/rest/gadget/1.0/login',
    'worklogs': '/rest/tempo-rest/1.0/worklogs/',
    'remaining_estimate': '/rest/tempo-rest/1.0/worklogs/remainingEstimate/calculate/',
}


class JiraTempoTimelogsDriver:
    def __init__(self, jira_url):
        self.jira_url = jira_url
        self.session = requests.Session()
        self.username = ''

    def get_url(self, endpoint):
        return self.jira_url + ENDPOINTS[endpoint]

    def login(self, username, password):
        request = self.session.post(
            self.get_url('login'),
            data={
                'os_username': username,
                'os_password': password,
            }
        )
        # print the html returned or something more intelligent to see if it's a successful login page.
        response = json.loads(request.text)
        if not response.get("loginSucceeded"):
            raise "Failed to log in."

        self.username = username

    @staticmethod
    def _format_date(date):
        return date.strftime("%d/%b/%y")

    @staticmethod
    def _format_time(time):
        hours, mod = divmod(time.seconds, 3600)
        minutes, sec = divmod(mod, 60)
        if sec > 30:
            minutes += 1

        output = ''
        if hours:
            output += '{}h'.format(hours)
        if minutes:
            output += '{}m'.format(minutes)
        return output

    def get_remaining_estimate(self, timelog):
        """
        Get remaining estimate from Jira
        """
        url_data = '{ticket}/{today}/{today}/{duration}?username={username}'
        extra_data = url_data.format(
            ticket=timelog.ticket,
            today=timelog.date.strftime("%Y-%m-%d"),
            # Then we have this ugly thing here
            duration='{}m'.format(int(timelog.time.seconds/60)),
            username=self.username,
        )

        # I need to start using proper methods to join urls
        response = self.session.get(self.get_url('remaining_estimate') + extra_data)

        # Check if answer is good, calculate and return remaining
        if response.status_code == 200:
            remaining = response.content.decode('UTF-8')
            if not remaining:
                return '0h'
            return remaining
        return False

    def add_timelog(self, timelog):
        """
        Timelog structured like this:
        {
            "ticket": "BB-0000",
            "date": DateObject,
            "time": TimeDelta,
            "description": "I did some work"
        }
        """

        remaining_estimate = self.get_remaining_estimate(timelog)
        payload = {
            'type': 'issue',
            'actionType': 'logTime',
            'use-ISO8061-week-numbers': False,
            'ansidate': timelog.date.strftime('%Y-%m-%d'),
            'ansienddate': timelog.date.strftime('%Y-%m-%d'),
            'tracker': False,
            'issue': 'BB-282',
            'planning': False,
            'selectedUser': self.username,
            'date': self._format_date(timelog.date),
            'enddate': self._format_date(timelog.date),
            'time': self._format_time(timelog.time),
            'remainingEstimate': remaining_estimate,
            'comment': timelog.description
        }

        response = self.session.post(
            self.get_url('worklogs') + timelog.ticket,
            data=payload
        )

        if 'valid="true"' in response.content.decode('UTF-8'):
            return True
        return False
