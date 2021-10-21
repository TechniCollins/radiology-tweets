from django.db import models


class Tweet(models.Model):
    tweet_id = models.CharField(max_length=50, unique=True)
    text = models.CharField(max_length=1000)
    # Tweet url is given by;
    # f"https://twitter.com/{{ to.author_username }}/status/{{ to.tweet_id }}"
    created_at = models.DateTimeField()  # in UTC
    language = models.CharField(max_length=10)

    mentions = models.CharField(max_length=1000)
    hashtags = models.CharField(max_length=1000)
    media = models.TextField()

    # Tweet metrics
    retweet_count = models.IntegerField()
    reply_count = models.IntegerField()
    like_count = models.IntegerField()
    quote_count = models.IntegerField()

    # No need to normalize author data because
    # we may potentially be dealing with big data.
    author_id = models.CharField(max_length=50)
    author_username = models.CharField(max_length=30)
    # Author url is given by;
    # f"https://twitter.com/{{ to.author_username }}"
    author_bio = models.CharField(max_length=1000)
    author_name = models.CharField(max_length=200)

    # Author metrics
    author_followers_count = models.IntegerField()
    author_following_count = models.IntegerField()
    author_tweet_count = models.IntegerField()

    # Delete these?
    reply_to = models.CharField(max_length=50, default=None, null=True)
    retweet_to = models.CharField(max_length=50, default=None, null=True)

    def __str__(self):
        return self.tweet_id

class Hashtag(models.Model):
    name = models.CharField(max_length=200, unique=True)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"# {str(self.name)}"
