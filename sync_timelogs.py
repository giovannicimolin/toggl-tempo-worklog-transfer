#!/usr/bin/env python
import argparse
import sys

import click

from csv import DictReader
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

def log_to_jira(timelogs):
   # Log time on Jira
   click.echo("Logging in on Jira... \n")
   tempo_driver = JiraTempoTimelogsDriver(config('JIRA_URL'))
   tempo_driver.login(config('JIRA_USER'), config('JIRA_PASSWORD'))

   with click.progressbar(
      timelogs,
      label='Logging time entries',
      item_show_func=lambda item: f"Logging time for {item.ticket}: {item.description}" if item  else ''
   ) as items:
      for timelog in items:
         if not tempo_driver.add_timelog(timelog):
            click.echo(click.style(f"Unable to log time for {timelog.ticket}", fg='red'))

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

def print_timelogs(timelogs):
   click.echo(click.style('Completed Timelogs:', bold=True))
   for timelog in timelogs['complete']:
      click.echo(timelog)
   click.echo(click.style('Incomplete Timelogs:', bold=True))
   for timelog in timelogs['incomplete']:
      click.echo(timelog)

@click.group()
@click.option('--dry-run', is_flag=True, help="Display log entries but do not submit")
@click.option('--verbose', '-v', default=False, help='Be verbose')
@click.pass_context
def cli(ctx, dry_run, verbose):
   ctx.ensure_object(dict)
   ctx.obj['dry-run'] = dry_run
   ctx.obj['verbose'] = verbose


@cli.command()
@click.option(
   '--distrubute', '-d', default=False, help='Redistribute incomplete on other tickets'
)
@click.option(
   '--start-date', '-s', default=None, help='Starting date, e.g. 2019-01-01'
)
@click.pass_context
def toggl(ctx, distribute, start_date):

   dry_run = ctx.obj['dry-run']
   verbose = ctx.obj['verbose']

   # Verbosity, needs work
   logf = lambda x: x
   if verbose:
      logf = print

   # Load last saved worklog if not date is supplied
   if start_date:
      start = datetime.strptime(start_date, r'%Y-%m-%d')
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
   if incomplete and distribute:
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

@cli.command()
@click.argument(
   'file', type=click.File('r')
)
@click.pass_context
def csv(ctx, file):
   dry_run = ctx.obj['dry-run']
   reader = DictReader(file)
   timelogs = list(reader)
   fields = set(timelogs[0].keys())
   missing_fields = {'ticket', 'date', 'time', 'description'} - fields
   if missing_fields:
      click.echo(f'All fields must be specified in the CSV file. The following fields are missing:')
      click.echo('\t' + '\n\t'.join(sorted(missing_fields)))
      ctx.exit()
   timelog_entries = {
      'incomplete': list(),
      'complete': csv_timelog_iter(timelogs),
   }
   if dry_run:
      print_timelogs(timelog_entries)
   else:
      log_to_jira(distribute_timelogs(timelog_entries))


def csv_timelog_iter(csv_data):
   for log_entry in csv_data:
      if log_entry.get('logged', '').lower() in ['yes', 'y', 'true']:
         continue
      if not log_entry.get('ticket'):
         continue
      yield TimeLogEntry(
         date=log_entry['date'],
         description=log_entry['description'],
         ticket=log_entry['ticket'].upper(),
         time=log_entry['time'],
      )

if __name__ == '__main__':
   cli()
