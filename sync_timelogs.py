#!/usr/bin/env python
import argparse
import sys

from datetime import datetime, timedelta, timezone
from dateutil import parser
from decouple import config
from libtoggl import TogglTimesheets, Timelog
from libtempo import JiraTempoTimelogsDriver


def distribute_incomplete(incomplete, complete, logf):
   """ Distribute time in incomplete in complete, weighted """
   current = [float(t.time.seconds) for t in complete]
   rates = [i / sum(current) for i in current]
   logf('\n---\n')
   logf('Incomplete timelogs found, distributing with rates:')
   logf('\n'.join('{} {} {}'.format(t.ticket, t.description, r) for t, r in zip(complete, rates)))
   for timelog in incomplete:
      logf('Distributing {}: {}'.format(
         timelog.time, ' '.join([str(rate * timelog.time) for rate in rates])
      ))
      for target, rate in zip(complete, rates):
         target.time += timelog.time * rate


def update_tempo(timelogs, logf):
   """ Update Jira """
   tempo_driver = JiraTempoTimelogsDriver(config('JIRA_URL'))
   tempo_driver.login(config('JIRA_USER'), config('JIRA_PASSWORD'))
   logf('\n---\n')
   for timelog in grouped:
      logf("Logging time for {}: {} ({}) ({})".format(
         timelog.ticket, timelog.description, timelog.date, timelog.time))
      if args.n:
         continue
      if not tempo_driver.add_timelog(timelog):
         print("Unable to log time for {}".format(timelog.ticket))
         return parser.parse(timelog.start).timestamp()


def group_timelogs(timelogs, logf):
   """ Group multiple timelogs with same ticket, description and date """
   cache = {}
   for timelog in timelogs:
      key = '{}:{}:{}'.format(timelog.ticket, timelog.description, timelog.date.date())
      logf("Found worklog {}: {} ({}) ({})".format(timelog.ticket, timelog.description, timelog.date, timelog.time))
      if key not in cache:
         cache[key] = timelog
      else:
         cache[key].time += timelog.time

   logf('\n---\n')
   for timelog in cache.values():
      logf("Grouped worklog {}: {} ({}) ({})".format(timelog.ticket, timelog.description, timelog.date, timelog.time))

   return cache.values()


def get_timelogs(start, end):
   """ Fetch timelogs from Toggle """
   toggl_driver = TogglTimesheets(config('TOGGL_TOKEN'))
   timelogs = toggl_driver.get_timelogs(start, end)
   return timelogs['complete'], timelogs['incomplete']


if __name__ == '__main__':
   # Define arguments
   argp = argparse.ArgumentParser()
   argp.add_argument('-d', action='store_true', help='Redistribute incomplete on other tickets')
   argp.add_argument('-n', action='store_true', help='Make no modifications')
   argp.add_argument('-v', action='store_true', help='Be verbose')
   argp.add_argument('-s', action='store', default=None, help='Starting date, e.g. 2019-01-01')
   args = argp.parse_args()

   # Verbosity, needs work
   logf = lambda x: x
   if args.v:
      logf = print

   # Load last saved worklog if not date is supplied
   if args.s:
      start = datetime.strptime(args.s, r'%Y-%m-%d')
   else:
      try:
         with open('.latest') as f:
            start = datetime.fromtimestamp(float(f.read()))
      except:
         print('ERROR: .latest not found, run with "-s YYYY-MM-DD"')
   # Set end to last midnight
   end = datetime.now().replace(hour=0, minute=0, second=0)

   # Fetch complete and incomplete timelogs
   complete, incomplete = get_timelogs(start, end)

   # Group completed
   grouped = group_timelogs(complete, logf)

   # Distribute incomplete
   if incomplete and args.d:
      distribute_incomplete(incomplete, grouped, logf)
   elif incomplete:
      print('ERROR:', 'cannot proceed with incomplete timelogs, verify or enable distribute (-d).')
      sys.exit(1)

   # This will update Tempo
   last = update_tempo(grouped, logf)
   if last:
      # Stopped before everything was processed
      end = last

   if not args.n:
      with open('.latest', 'w') as f:
         f.write(str(end.timestamp()))
