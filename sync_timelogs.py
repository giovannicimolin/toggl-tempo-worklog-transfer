from datetime import datetime

from decouple import config
from libtoggl import TogglTimesheets
from libtempo import JiraTempoTimelogsDriver


toggl_driver = TogglTimesheets(config('TOGGL_TOKEN'))
tempo_driver = JiraTempoTimelogsDriver(config('JIRA_URL'))

# Get timelogs from Toggl
# timelogs = toggl_driver.get_timelogs_last_n_days(1)

# Use this if you want to set a date
timelogs = toggl_driver.get_timelogs(
    datetime(2019, 5, 20, 0, 0, 0, 0),
    datetime(2019, 5, 20, 23, 59, 0, 0)
)

# Log time on Jira
print("Logging in on Jira... \n\n")
tempo_driver.login(config('JIRA_USER'), config('JIRA_PASSWORD'))

for timelog in timelogs['complete']:
    print("Logging time for {}: {}...".format(timelog.ticket, timelog.description))
    if not tempo_driver.add_timelog(timelog):
        print("Unable to log time for {}".format(timelog.ticket))
