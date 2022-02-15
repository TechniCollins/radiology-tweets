*NOTE:* This was originally built to study discussions about radiology on Twitter. A lot of traces of the previous use case still remain.

# PREREQUISITES

## Google Developer account

You'll need a service account to make changes to spreadsheets. Use [this](https://console.cloud.google.com/iam-admin/serviceaccounts/create) link to create the required project and credentials. Credentials will be downloaded to your local machine. Save the credentials file as `credentials.json` to `twitter_client/management/commands/`.

## Twitter Develper account

You'll need this to get tweets. If you don't have an account, create on [here](https://developer.twitter.com/en/apply/user.html). Create a project with access to API version 2 and generate a bearer token. Add the bearer token to `BEARER_TOKEN` environment variable. If you have an academic bearer token add it to the `ACADEMIC_BEARER_TOKEN` variable.

## Digital Ocean Server

Create an account [here](https://m.do.co/c/c244ac4077e3) then create a droplet from which your script will run.

# INSTALLATION

## Spreadsheet

Create a spreadsheet on Google Drive and copy its ID from the address bar to the `SPREADSHEET_ID` env variable. Share the created spreadsheet with the service's email and give edit access.

## Requirements

Install requirements from the requirements file;

	pip install -r requirements.txt


# USAGE


## Cron job

Write this cron job to allow the script to run everyday.

    0 0 * * * cd /path/to/project && docker-compose exec web python manage.py get_tweets


## Getting Full Archive via Academic Research API

You can do this from the User Interface or by running the following command directly;

    docker-compose exec web python manage.py get_tweets --endpoint=academic --fromdate=202011270000 --todate=202110232359


## Get replies to the tweets returned

You can choose to also get replies to tweets by passing the `--get_replies` command line argument. For the academic track, you can also do this from the UI.

    0 0 * * * cd /path/to/project && docker-compose exec web python manage.py get_tweets --get_replies


## Include Retweets

By default, retweets are not included. To get tweets with the specified hashtags/keywords, even if they are retweets, add the `--include_retweets` command line argument. For the academic track, you can also do this from the UI.

    0 0 * * * cd /path/to/project && docker-compose exec web python manage.py get_tweets --get_replies

