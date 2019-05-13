import json
import requests


ENDPOINTS = {
    'login': '/rest/gadget/1.0/login'
    'worklogs': 'rest/tempo-timesheets/3/worklogs/'
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
            raise("Failed to log in.")

        self.username = username

    def _format_date(self, date):
        return date.strftime("%Y-%m-%dT00:00:00.000+0000")

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
        payload = {
            "dateStarted": self._format_date(timelog.date),
            "comment": timelog.description,
            "issue": {
              "key": timelog.ticket,
            },
            "author":{
                "name": self.username,
            },
            "timeSpentSeconds": timelog.time.seconds
        }
        response = self.session.post(
            self.get_url('worklogs'),
            headers={
                'content-type': 'application/json'
            },
            data=json.dumps(payload)
        )
        if response.status_code == 200:
            return True
        return False
