import sys

from const import TIMELOG
from datetime import datetime, timedelta, timezone
from decouple import config
from libtoggl import TogglTimesheets
from libtempo import JiraTempoTimelogsDriver


def yes_no_question(msg):
    # raw_input returns the empty string for "enter"
    yes = {'yes','y', 'ye', ''}
    no = {'no','n'}

    choice = raw_input(msg).lower()
    if choice in yes:
       return True
    elif choice in no:
       return False
    else:
       sys.stdout.write("Please respond with 'yes' or 'no'")


toggl_driver = TogglTimesheets(config('TOGGL_TOKEN'))
tempo_driver = JiraTempoTimelogsDriver(config('JIRA_URL'))

# Get timelogs from Toggl
timelogs = toggl_driver.get_timelogs_last_n_days(1)

# Use this if you want to set a date
# timelogs = toggl_driver.get_timelogs(
#     datetime(2019, 5, 17, 0, 0, 0, 0),
#     datetime(2019, 5, 17, 23, 59, 0, 0)
# )

if timelogs['incomplete']:
    distribute = yes_no_question("You have timelogs whitout issues. Do you want to distribute the time between your other tickets?")
    if distribute:
        # todo
        pass

# Log time on Jira
print("Logging in on Jira... \n\n")
tempo_driver.login(config('JIRA_USER'), config('JIRA_PASSWORD'))

for timelog in timelogs['complete']:
    print("Logging time for {}: {}...".format(timelog.ticket, timelog.description))
    if not tempo_driver.add_timelog(timelog):
        print("Unable to log time for {}".format(timelog.ticket))
