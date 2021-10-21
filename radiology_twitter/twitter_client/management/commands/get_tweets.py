from django.core.management.base import BaseCommand
from django.utils import timezone

import os
from pathlib import Path
import requests
import time

import csv

# for working with date and time
import datetime

from googleapiclient.discovery import build
from google.oauth2 import service_account

from twitter_client.models import (Hashtag, Tweet)


class Command(BaseCommand):
    help = 'Queries the twitter API for tweets'

    def add_arguments(self, parser):
        parser.add_argument('--get_replies', action='store_true')
        parser.add_argument('--include_retweets', action='store_true')
        parser.add_argument('--endpoint', type=str, default='standard')


    def getReplies(self, tweet_id, author):
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
    def organizeMedia(self, media_objects):
        media_dict = {}

        if media_objects:
            for media in media_objects:
                media_dict[media.get("media_key")] = media.get("url", '')

        return media_dict


    def organizeAuthors(self, author_objects):
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


    def processTweets(self, tweets_object, get_replies):
        # A list of tweet instances to bulk insert later
        tweet_instances = []

        try:
            tweets = tweets_object.get("data")
            media_objects = self.organizeMedia(tweets_object.get("includes", {}).get("media"))
            author_objects = self.organizeAuthors(tweets_object.get("includes", {}).get("users"))

            for tweet in tweets:
                # Primary tweet attributes
                tweet_id = tweet.get("id")
                text = tweet.get("text")
                date = str(tweet.get("created_at"))

                author = author_objects.get(tweet.get("author_id"))

                # tweet metrics
                metrics = tweet.get("public_metrics")

                if get_replies:
                    # Check for replies
                    if int(metrics.get("reply_count")) > 0:
                        replies = self.getReplies(tweet_id, author)
                    else:
                        replies = []

                entities = tweet.get("entities", {})

                language = tweet.get("lang")

                hashtags_list = entities.get("hashtags", [])
                hashtags = [f'#{h.get("tag")}' for h in hashtags_list]

                mentions_list = entities.get("mentions", [])
                mentions = [f'@{m.get("username")}' for m in mentions_list]

                media_ids = (tweet.get("attachments", {})).get("media_keys", [])
                media = [media_objects.get(m) for m in media_ids]

                # create a link to the tweet
                url = f"https://twitter.com/{author.get('username')}/status/{tweet_id}"

                tweet_instances.append(
                    Tweet(
                        tweet_id = str(tweet_id),
                        text = text,
                        # Tweet url is given by;
                        # f"https://twitter.com/{{ to.author_username }}/status/{{ to.tweet_id }}"
                        created_at = date,  # in UTC
                        language = language,
                        mentions = ",".join(mentions),
                        hashtags = ",".join(hashtags),
                        media = ",".join(media),
                        # Tweet metrics
                        retweet_count = metrics.get("retweet_count"),
                        reply_count = metrics.get("reply_count"),
                        like_count = metrics.get("like_count"),
                        quote_count = metrics.get("quote_count"),
                        # No need to normalize author data because
                        # we may potentially be dealing with big data.
                        author_id = tweet.get("author_id"),
                        author_username = author.get("username"),
                        # Author url is given by;
                        # f"https://twitter.com/{{ to.author_username }}"
                        author_bio = author.get("bio"),
                        author_name = author.get("name"),
                        # Author metrics
                        author_followers_count = author.get("metrics").get("followers_count"),
                        author_following_count = author.get("metrics").get("following_count"),
                        author_tweet_count = author.get("metrics").get("tweet_count")
                    )
                )

                # retweet_to = 

                if get_replies:
                    # reply_to = 
                    if replies:
                        for reply in replies:
                            tweet_instances.append(reply)

            # Bulk insert tweets
            Tweet.objects.bulk_create(tweet_instances, ignore_conflicts=True)

            return 1  # Just return something to differentiate success and failure

        except Exception as e:
            with open("error.txt", "a") as f:
                f.write(f'{datetime.datetime.now()}: Failed to process tweet: {e}\n')

                return None


    # next_token_after_limit param only applies when
    # trying to recover from rate limit reached error
    def getTweets(self, endpoint, query, get_replies=False, next_token_after_limit=None):
        if endpoint == "academic":
            url = "https://api.twitter.com/2/tweets/search/all"
            bearer_token = os.environ.get('ACADEMIC_BEARER_TOKEN')
        else:
            url = "https://api.twitter.com/2/tweets/search/recent"
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
                url,
                params=payload,
                headers=headers
            )

            if int(response.status_code) != 200:
                if int(response.status_code) == 429:            
                    # if we have reached the rate limit,
                    # sleep for a minute then call function again
                    # indicating where to start
                    print("Rate limit reached. Sleeping")
                    time.sleep(60)
                    print("Proceeding...")
                    self.getTweets(endpoint, query, get_replies, next_token)
                else:
                    with open("error.txt", "a") as f:
                        f.write(f'{datetime.datetime.now()}: {response.status_code}: {response.text}\n')
            else:
                tweets_object = response.json()

                self.processTweets(tweets_object, get_replies)

                # Assumption is we won't reach rate limit on the first
                # attempt, so next_token will be defined by the time
                # we need it.
                next_token = tweets_object.get("meta").get("next_token")

                if next_token:
                    payload["next_token"] = next_token
                else:
                    has_next_page = False

    
    def getTweetVolumes(self, endpoint, query):
        if endpoint != "academic":
            print("Tweet volumes are only available for the academic track")
            return

        bearer_token = os.environ.get('ACADEMIC_BEARER_TOKEN')

        headers = {
            "Authorization": f"Bearer {bearer_token}"
        }

        payload = {
            "query": query,
        }

        url = 'https://api.twitter.com/2/tweets/counts/all'

        response = requests.get(
            url,
            params=payload,
            headers=headers
        )

        return


    def getHashtags(self):
        hashtags = [x.name for x in Hashtag.objects.filter(enabled=True)]

        return hashtags

    def handle(self, *args, **options):
        endpoint = options['endpoint']
        get_replies = options['get_replies']
        include_retweets = options['include_retweets']

        hashtags = self.getHashtags()

        if include_retweets:
            query = f"{' OR '.join([f'#{x}' for x in hashtags])}"
        else:
            query = f"-is:retweet ({' OR '.join([f'#{x}' for x in hashtags])})"


        self.getTweetVolumes(endpoint, query)
        exit()

        query_length = len(query)

        if query_length > 512:
            print("There are too many hashtags.")
        else:
            print(f"Querying Twitter, Please Wait...")
            self.getTweets(endpoint, query)
            print("\nDONE")
