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

from twitter_client.models import (
    Hashtag, Tweet,
    TweetHashtagMap, Volume
)


class Command(BaseCommand):
    help = 'Queries the twitter API for tweets'

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

    def add_arguments(self, parser):
        parser.add_argument('--get_replies', action='store_true')
        parser.add_argument('--include_retweets', action='store_true')
        parser.add_argument('--endpoint', type=str, default='standard')
        parser.add_argument('--start_time', type=str)
        parser.add_argument('--end_time', type=str)

    
    def getToken(self, endpoint):
        if endpoint == "academic":
            url = "https://api.twitter.com/2/tweets/search/all"
            bearer_token = os.environ.get('ACADEMIC_BEARER_TOKEN')
        else:
            url = "https://api.twitter.com/2/tweets/search/recent"
            bearer_token = os.environ.get('BEARER_TOKEN')

        return (url, bearer_token)


    def createPayloadAndHeaders(self, endpoint, query, hashtag, timespan=None):
        token = self.getToken(endpoint)

        headers = {
            "Authorization": f"Bearer {token[1]}"
        }

        payload = {
            "query": query,
            "expansions": ",".join(self.expansions),
            "max_results": 100,
            "media.fields": ",".join(self.media_fields),
            "tweet.fields": ",".join(self.tweet_fields),
            "user.fields": ",".join(self.user_fields)
        }

        if timespan:
            payload['start_time'] = timespan.get('start_time')
            payload['end_time'] = timespan.get('end_time')

        if endpoint == "standard" and hashtag.last_tweet:
            payload['since_id'] = hashtag.last_tweet

        return (token[0], payload, headers)


    # This function will handle making requests,
    # paginating through responses and trying to
    # recover from rate limits
    def paginate(self, url, payload, headers):
        has_next_page = True

        while has_next_page:
            response = requests.get(
                url,
                params=payload,
                headers=headers
            )

            if int(response.status_code) == 200:
                next_token = response.json().get("meta").get("next_token")

                if next_token:
                    payload["next_token"] = next_token
                else:
                    has_next_page = False

                yield response.json()

            else:
                if int(response.status_code) == 429:            
                    # if we have reached the rate limit,
                    # sleep for a minute then call function again
                    print("Rate limit reached. Sleeping")
                    time.sleep(60)
                    print("Proceeding...")
                    self.paginate(url, payload, headers)

                else:
                    raise Exception(response.status_code, response.text)


    def getReplies(self, endpoint, hashtag, tweet_id, author):
        try:
            print(f"Getting replies for {tweet_id}")

            query = f'conversation_id:{tweet_id} to:{author}'

            """
               Query Explanation

               A tweet that's a reply will have a conversation id leading back to
               the original tweet, and will be in reply to the user that published it
            """

            payload = self.createPayloadAndHeaders(endpoint, query, hashtag)

            for page in self.paginate(payload[0], payload[1], payload[2]):
                self.processTweets(endpoint, hashtag, page, True)

        except Exception as e:
            with open("error.txt", "a") as f:
                f.write(f'{datetime.datetime.now()}: Failed to get replies for tweet with ID {tweet_id}: {e}\n')

        return

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


    def processTweets(self, endpoint, hashtag, page, get_replies):
        try:
            tweets = page.get("data", [])
            media_objects = self.organizeMedia(page.get("includes", {}).get("media"))
            author_objects = self.organizeAuthors(page.get("includes", {}).get("users"))

            tweet_id = None

            for tweet in tweets:
                # Primary tweet attributes
                tweet_id = tweet.get("id")
                print(tweet_id)
                text = tweet.get("text")
                date = str(tweet.get("created_at"))

                author = author_objects.get(tweet.get("author_id"))

                # tweet metrics
                metrics = tweet.get("public_metrics")

                if get_replies:
                    if int(metrics.get("reply_count")) > 0:
                        self.getReplies(endpoint, hashtag, tweet_id, tweet.get("author_id"))

                retweet_to = None
                reply_to = None
                quoted_tweet = None

                referenced_tweets = tweet.get("referenced_tweets", [])

                for rt in referenced_tweets:
                    if rt.get("type") == "retweeted":
                        retweet_to = rt.get("id")
                    elif rt.get("type") == "replied_to":
                        reply_to = rt.get("id")
                    elif rt.get("type") == "quoted_tweet":
                        quoted_tweet = rt.get("id")
                    else:
                        pass

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

                tweet_instance = Tweet.objects.get_or_create(
                    tweet_id = str(tweet_id),
                    defaults={
                        "text": text,
                        # Tweet url is given by;
                        # f"https://twitter.com/{{ to.author_username }}/status/{{ to.tweet_id }}"
                        "created_at": date,  # in UTC
                        "language": language,
                        "mentions": ",".join(mentions),
                        "hashtags": ",".join(hashtags),
                        "media": ",".join(media),
                        # Tweet metrics
                        "retweet_count": metrics.get("retweet_count"),
                        "reply_count": metrics.get("reply_count"),
                        "like_count": metrics.get("like_count"),
                        "quote_count": metrics.get("quote_count"),
                        # No need to normalize author data because
                        # we may potentially be dealing with big data.
                        "author_id": tweet.get("author_id"),
                        "author_username": author.get("username"),
                        # Author url is given by;
                        # f"https://twitter.com/{{ to.author_username }}"
                        "author_bio": author.get("bio"),
                        "author_name": author.get("name"),
                        # Author metrics
                        "author_followers_count": author.get("metrics").get("followers_count"),
                        "author_following_count": author.get("metrics").get("following_count"),
                        "author_tweet_count": author.get("metrics").get("tweet_count"),
                        "reply_to": reply_to,
                        "retweet_to": retweet_to,
                        "quoted_tweet": quoted_tweet
                    }
                )

                TweetHashtagMap.objects.get_or_create(
                    tweet=tweet_instance[0],
                    hashtag=hashtag
                )

            if tweet_id:
                hashtag.last_tweet=tweet_id
                hashtag.save()

            return 1  # Just return something to differentiate success and failure

        except Exception as e:
            with open("error.txt", "a") as f:
                f.write(f'{datetime.datetime.now()}: Failed to process tweet: {e}\n')

                return None


    def getTweets(self, endpoint, query, timespan, hashtag, get_replies=False):
        payload = self.createPayloadAndHeaders(endpoint, query, hashtag, timespan)
        # This returns (url, payload, headers)

        for page in self.paginate(payload[0], payload[1], payload[2]):
            self.processTweets(endpoint, hashtag, page, get_replies)

    
    def getTweetVolumes(self, endpoint, query, timespan, hashtag):
        bearer_token = os.environ.get('ACADEMIC_BEARER_TOKEN')

        headers = {
            "Authorization": f"Bearer {bearer_token}"
        }

        payload = {
            "query": query,
        }

        if timespan:
            payload['start_time'] = timespan.get('start_time')
            payload['end_time'] = timespan.get('end_time')

        url = 'https://api.twitter.com/2/tweets/counts/all'

        for page in self.paginate(url, payload, headers):
            volume_objects = []

            for x in page.get("data", []):
                volume_objects.append(
                    Volume(
                        hashtag=hashtag,
                        start_time=x.get("start"),
                        end_time=x.get("end"),
                        tweet_count=x.get("tweet_count")
                    )
                )

            Volume.objects.bulk_create(volume_objects)

        return


    def getHashtags(self, endpoint):
        if endpoint == "academic":
            hashtags = Hashtag.objects.filter(
                    enabled=True,
                    endpoint__name="academic"
            )
        else:
            hashtags = Hashtag.objects.filter(
                    enabled=True,
                    endpoint__name="standard"
            )

        return hashtags

    def handle(self, *args, **options):
        endpoint = options['endpoint']
        get_replies = options['get_replies']
        include_retweets = options['include_retweets']

        start_time = options['start_time']
        end_time = options['end_time']

        hashtags = self.getHashtags(endpoint)

        for hashtag in hashtags:
            if include_retweets:
                query = f"#{hashtag.name}"
            else:
                query = f"-is:retweet #{hashtag.name}"

            if start_time and end_time:
                timespan = {"start_time": start_time, "end_time": end_time}
            else:
                timespan = None

            print(f"Querying Twitter for #{hashtag.name}")
            self.getTweets(endpoint, query, timespan, hashtag, get_replies)

            if endpoint == "academic":
                self.getTweetVolumes(endpoint, query, timespan, hashtag)
        
        print("\nDONE")
