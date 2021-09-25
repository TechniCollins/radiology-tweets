import os
from pathlib import Path
import requests
import time

import csv

# for working with date and time
import datetime

from googleapiclient.discovery import build
from google.oauth2 import service_account

# Google API key
google_api_key = os.environ.get('GOOGLE_API_KEY')

BASE_DIR = Path(__file__).resolve().parent

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = f"{BASE_DIR}/credentials.json"

credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# bearer token authentication
bearer_token = os.environ.get('BEARER_TOKEN')

# The tweet attributes to be returned by the API
tweet_fields = [
    'id', 'text', 'created_at', 'public_metrics', 'lang',
    'referenced_tweets', 'entities', 'geo', 'attachments'
]

media_fields = [
    'url'
]

# The user attributes to be returned by the API

expansions = [
    'author_id',
    'attachments.media_keys'
]

user_fields = [
    'name', 'username', 'public_metrics',
    'description'
]


def getReplies(tweet_id, author):
    try:
        # create a list to store all replies
        replies = []

        # Form the search query
        query = f'conversation_id:{tweet_id} to:{author}'

        """
           Query Explanation

           A tweet that's a reply will have a conversation id leading back to
           the original tweet, and will be in reply to the user that published it
        """

        # This will help us paginate
        has_next_page = True

        headers = {
            "Authorization": f"Bearer {bearer_token}"
        }

        payload = {
            "query": query,
            "max_results": 100,
            "tweet.fields": "text,id"
        }

        while has_next_page:
            tweets_object = requests.get(
                "https://api.twitter.com/2/tweets/search/recent",
                params=payload,
                headers=headers
            ).json()

            tweets = tweets_object.get("data", [])

            for tweet in tweets:
                replies.append(
                    ["", "", "", "", "", "", "", "", "", "", "", tweet.get("text")]
                )

            next_token = tweets_object.get("meta").get("next_token")

            if next_token:
                payload["next_token"] = next_token
            else:
                has_next_page = False

        return replies

    except Exception as e:
        with open("error.txt", "a") as f:
            f.write(f'{datetime.datetime.now()}: Failed to get replies for tweet with ID {tweet_id}: {e}\n')

        return None


"""
The Twitter API V2 returns media in
an unorthodox way. Let's re-organize
the data for ease of querying
"""
def organizeMedia(media_objects):
    media_dict = {}

    if media_objects:
        for media in media_objects:
            media_dict[media.get("media_key")] = media.get("url", '')

    return media_dict


def organizeAuthors(author_objects):
    author_dict = {}

    if author_objects:
        for author in author_objects:
            author_dict[author.get("id")] = {
                "username": author.get("username"),
                "url": f"https://twitter.com/{author.get('username')}",
                "bio": author.get("description"),
                "name": author.get("name"),
                "metrics": author.get("public_metrics")
            }

    return author_dict


def processTweets(tweets_object, include_replies):
    try:
        tweets = tweets_object.get("data")
        media_objects = organizeMedia(tweets_object.get("includes", {}).get("media"))
        author_objects = organizeAuthors(tweets_object.get("includes", {}).get("users"))

        with build('sheets', 'v4', credentials=credentials) as service:
            tweets_list = []

            for tweet in tweets:
                # Primary tweet attributes
                tweet_id = tweet.get("id")
                text = tweet.get("text")
                date = str(tweet.get("created_at"))

                author = author_objects.get(tweet.get("author_id"))

                # tweet metrics
                metrics = tweet.get("public_metrics")


                if include_replies:
                    # Check for replies
                    if int(metrics.get("reply_count")) > 0:
                        replies = getReplies(tweet_id, author)
                    else:
                        replies = []

                entities = tweet.get("entities")

                language = tweet.get("lang")

                hashtags_list = entities.get("hashtags", [])
                hashtags = [f'#{h.get("tag")}' for h in hashtags_list]

                mentions_list = entities.get("mentions", [])
                mentions = [f'@{m.get("username")}' for m in mentions_list]

                media_ids = (tweet.get("attachments", {})).get("media_keys", [])
                media = [media_objects.get(m) for m in media_ids]

                # create a link to the tweet
                url = f"https://twitter.com/{author.get('username')}/status/{tweet_id}"

                tweets_list.append(
                    [
                        str(tweet_id), text, url,
                        date, language,
                        author.get("username"),
                        author.get("url"),
                        author.get("bio"),
                        author.get("name"),
                        author.get("metrics").get("followers_count"),
                        author.get("metrics").get("following_count"),
                        author.get("metrics").get("tweet_count"),
                        metrics.get("retweet_count"),
                        metrics.get("reply_count"),
                        metrics.get("like_count"),
                        metrics.get("quote_count"),
                        ", ".join(mentions),
                        ", ".join(hashtags),
                        ", ".join(media)
                    ]
                )

                if include_replies:
                    if replies:
                        tweets_list.append(["", "", "", "", "", "", "", "", "", "", "", "REPLIES"])
                        for reply in replies:
                            tweets_list.append(reply)

            # Write to sheets
            resource = {
              "majorDimension": "ROWS",
              "values": tweets_list
            }
            spreadsheet_id = os.environ.get("SPREADSHEET_ID")
            service.spreadsheets().values().append(
              spreadsheetId=spreadsheet_id,
              range="Sheet1!A:A",
              body=resource,
              valueInputOption="USER_ENTERED"
            ).execute()

        return 1  # Just return something to differentiate success and failure

    except Exception as e:
        with open("error.txt", "a") as f:
            f.write(f'{datetime.datetime.now()}: Failed to process tweet: {e}\n')

            return None


# next_token_after_limit param only applies when
# trying to recover from rate limit reached error
def getTweets(query, include_replies=False, next_token_after_limit=None):
    # This will help us paginate
    has_next_page = True

    headers = {
        "Authorization": f"Bearer {bearer_token}"
    }

    payload = {
        "query": query,
        "expansions": ",".join(expansions),
        "max_results": 100,
        "media.fields": ",".join(media_fields),
        "tweet.fields": ",".join(tweet_fields),
        "user.fields": ",".join(user_fields)
    }

    # if we're recovering from a rate limit error
    if next_token_after_limit:
        payload['next_token'] = next_token

    while has_next_page:
        response = requests.get(
            "https://api.twitter.com/2/tweets/search/recent",
            params=payload,
            headers=headers
        )

        if int(response.status_code) == 429:            
            # if we have reached the rate limit,
            # sleep for a minute then call function again
            # indicating where to start
            print("Rate limit reached. Sleeping")
            time.sleep(60)
            print("Proceeding...")
            getTweets(query, include_replies, next_token)
        else:
            tweets_object = response.json()

            processTweets(tweets_object, include_replies)

            # Assumption is we won't reach rate limit on the first
            # attempt, so next_token will be defined by the time
            # we need it.
            next_token = tweets_object.get("meta").get("next_token")

            if next_token:
                payload["next_token"] = next_token
            else:
                has_next_page = False


def getHashtags():
    with open("radiology_hashtags.txt", "r") as f:
        hashtags = (f.read()).split("\n")

    return hashtags

if __name__ == '__main__':
    # Form query and get tweets
    hashtags = getHashtags()
    query = f"-is:retweet ({' OR '.join(hashtags)})"
    query_length = len(query)

    if query_length > 512:
        print("There are too many hashtags.")
    else:
        print(f"Querying Twitter, Please Wait...")
        getTweets(query)
        print("\nDONE")
