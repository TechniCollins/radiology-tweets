import os
import requests

import csv

# for working with date and time
import datetime

# bearer token authentication
bearer_token = os.environ.get('BEARER_TOKEN')

# The tweet attributes to be returned by the API
tweet_fields = [
    'id', 'text', 'created_at', 'public_metrics',
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
            media_dict[media.get("media_key")] = media.get("url")

    return media_dict


def processTweets(tweets_object, tweets_file):
    try:
        tweets = tweets_object.get("data")
        media_objects = organizeMedia(tweets_object.get("includes", {}).get("media"))

        with open(tweets_file, "a", newline='') as tf:
            writer = csv.writer(tf)

            for tweet in tweets:
                # Primary tweet attributes
                tweet_id = tweet.get("id")
                text = tweet.get("text")
                date = str(tweet.get("created_at"))

                author = tweet.get("author_id")

                # tweet metrics
                metrics = tweet.get("public_metrics")

                # Check for replies
                replies = getReplies(tweet_id, author)

                entities = tweet.get("entities")

                hashtags_list = entities.get("hashtags", [])
                hashtags = [f'#{h.get("tag")}' for h in hashtags_list]

                mentions_list = entities.get("mentions", [])
                mentions = [f'@{m.get("username")}' for m in mentions_list]

                media_ids = (tweet.get("attachments", {})).get("media_keys", [])
                media = [media_objects.get(m) for m in media_ids]

                # create a link to the tweet
                url = f"https://twitter.com/{author}/status/{tweet_id}"

                writer.writerow(
                    [
                        str(tweet_id), text, url,
                        date, str(author),
                        metrics.get("retweet_count"),
                        metrics.get("reply_count"),
                        metrics.get("like_count"),
                        metrics.get("quote_count"),
                        ", ".join(mentions),
                        ", ".join(hashtags),
                        ", ".join(media)
                    ]
                )

                if replies:
                    writer.writerow(["", "", "", "", "", "", "", "", "", "", "", "REPLIES"])
                    for reply in replies:
                        writer.writerow(reply)

        return 1  # Just return something to differentiate success and failure

    except Exception as e:
        with open("error.txt", "a") as f:
            f.write(f'{datetime.datetime.now()}: Failed to process tweet: {e}\n')

            return None


def getTweets(query):
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
        "tweet.fields": ",".join(tweet_fields)
    }

    while has_next_page:
        tweets_object = requests.get(
            "https://api.twitter.com/2/tweets/search/recent",
            params=payload,
            headers=headers
        ).json()

        processTweets(tweets_object, 'tweets.csv')
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
    query = " OR ".join(hashtags)
    query_length = len(query)

    if query_length > 512:
        print("There are too many hashtags.")
    else:
        print(f"Querying Twitter... ")
        getTweets(query)
        print("\nDONE")
