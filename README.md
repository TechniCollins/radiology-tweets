# PREREQUISITES

## Google Developer account

You'll need a service account to make changes to spreadsheets. Use [this](https://console.cloud.google.com/iam-admin/serviceaccounts/create) link to create the required project and credentials. Credentials will be downloaded to your local machine. Save the credentials file as `credentials.json` to `twitter_client/management/commands/`.

## Twitter Develper account

You'll need this to get tweets. If you don't have an account, create on [here](https://developer.twitter.com/en/apply/user.html). Create a project with access to API version 2 and generate a bearer token. Add the bearer token to `BEARER_TOKEN` environment variable.

## Digital Ocean Server

Create an account [here](https://m.do.co/c/c244ac4077e3) then create a droplet from which your script will run.

# INSTALLATION

## Spreadsheet

Create a spreadsheet on Google Drive and copy its ID from the address bar to the `SPREADSHEET_ID` env variable. Share the created spreadsheet with the service's email and give edit access.

## Requirements

Install requirements from the requirements file;

	pip install -r requirements.txt


## Cron job

Write this cron job to allow the script to run every Monday.

    0 0 * * 1 cd /path/to/project && source env/bin/activate && python get_tweets.py

