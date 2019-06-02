# Toggl to Jira timelog transfer

This is a little script that helps add Toggl timelogs to Jira.
My workflow is this: I use the description field as normally and add the ticket number on the tags (because they are easy to add).
Additionaly, I add a DD or FF flag to signal when work was done for those roles, but I'm not using that yet.

## How to use
1. Create a venv and install requirements with
```
pip install -r requirements.txt
```

2. Set up a `.env` file with these variables:
```
TOGGL_TOKEN=

JIRA_URL=
JIRA_USER=
JIRA_PASSWORD=
```
You'll need to get your Toggl API token from the account settings.
Add `JIRA_URL` without a trailing slash.

3. Change this line on `sync_timelogs.py` to set the number of days you want to sync:
```
timelogs = toggl_driver.get_timelogs_last_n_days(1)
```

4. Run it:
```
python sync_timelogs.py
```

## Warning
This is still on early work, so if it hits any error, it'll probably stop.
Make sure you check you timelogs for the correct format before syncing.

## Contributors
Thanks for everyone who contributed with this and helped make it better!

- @viadanna for polishing the code and taking care of all my todos
- @xitij2000 for a draft PR showing how to add additional functionalities
