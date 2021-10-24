from django.db import models
from django.core.validators import MinLengthValidator
from django.db.models import UniqueConstraint


class Endpoint(models.Model):
    name = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class Hashtag(models.Model):
    name = models.CharField(max_length=200, validators=[MinLengthValidator(limit_value=2)])
    # minimum length is 2 i.e a hashtag and at least 1 character
    enabled = models.BooleanField(default=True)
    endpoint = models.ForeignKey(Endpoint, on_delete=models.CASCADE)

    last_tweet = models.CharField(max_length=50, null=True)
    # last_tweet will be updated for all, but will be relevant
    # only for hashtags in the "standard" endpoint. We'll use
    # this as the `since_id`

    class meta:
        UniqueConstraint(fields = ['name', 'endpoint'], name = 'unique_hashtag')

    def __str__(self):
        return f"# {str(self.name)}"


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

    reply_to = models.CharField(max_length=50, default=None, null=True)
    retweet_to = models.CharField(max_length=50, default=None, null=True)
    quoted_tweet = models.CharField(max_length=50, default=None, null=True)

    def __str__(self):
        return self.tweet_id


class TweetHashtagMap(models.Model):
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE)
    hashtag = models.ForeignKey(Hashtag, on_delete=models.CASCADE)

    class meta:
        UniqueConstraint(fields = ['tweet', 'hashtag'], name = 'unique_hashtag')


class Volume(models.Model):
    hashtag = models.ForeignKey(Hashtag, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    tweet_count = models.IntegerField()
