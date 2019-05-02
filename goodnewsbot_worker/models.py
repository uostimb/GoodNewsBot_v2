from django.contrib.contenttypes.models import ContentType
from django.db import models
from model_utils.choices import Choices
from model_utils.models import TimeStampedModel


class SourceToReadManager(models.Manager):
    def active(self):
        return super().get_queryset().filter(disabled=False)


class SubredditsToRead(TimeStampedModel):
    """Model to store subreddits to fetch news posts from"""
    subreddit_name = models.CharField(max_length=32)
    post_limit = models.IntegerField()
    disabled = models.BooleanField(default=False)

    objects = SourceToReadManager()

    def __str__(self):
        ret_str = f"{self.subreddit_name} ({self.post_limit} posts)"
        if self.disabled:
            ret_str += " [DISABLED]"
        return ret_str


class RSSToRead(TimeStampedModel):
    """"
    Model to store RSS sources to fetch news posts from
    """
    url = models.URLField()
    disabled = models.BooleanField(default=False)

    objects = SourceToReadManager()

    def __str__(self):
        ret = {self.url}
        if self.disabled:
            ret += " [DISABLED]"
        return ret


class SubredditsToPostTo(models.Model):
    """
    Subreddits that GoodNewBot can post to
    """
    subreddit_name = models.CharField(
        max_length=32,
        unique=True,
    )

    def __str__(self):
        return self.subreddit_name


class Sentiment(models.Model):
    """
    Possible Sentiments and the cut off value above which we have confidence
    in the analysed sentiment
    """
    sentiment = models.CharField(
        max_length=10,
        unique=True,
    )
    cutoff = models.DecimalField(
        max_digits=6,
        decimal_places=5,
    )
    subreddit_to_post_to = models.ForeignKey(
        null=True,
        to="goodnewsbot_worker.SubredditsToPostTo",
        on_delete=models.SET_NULL,
        related_name="sentiment",
    )

    def __str__(self):
        return f"{self.sentiment} (>{self.cutoff})"


class SentimentAnalysis(TimeStampedModel):
    """
    Model to hold sentiment analysis data, and which (if any) of our subreddits
    the news was posted to
    """
    analysed_sentiment2 = models.ForeignKey(
        null=True,
        to="goodnewsbot_worker.Sentiment",
        on_delete=models.SET_NULL,
        related_name="source",
    )
    quantified_positive = models.DecimalField(
        null=True,
        blank=True,
        max_digits=21,
        decimal_places=19,
    )
    quantified_negative = models.DecimalField(
        null=True,
        blank=True,
        max_digits=21,
        decimal_places=19,
    )
    quantified_neutral = models.DecimalField(
        null=True,
        blank=True,
        max_digits=21,
        decimal_places=19,
    )
    quantified_mixed = models.DecimalField(
        null=True,
        blank=True,
        max_digits=21,
        decimal_places=19,
    )
    subreddit_posted_to = models.ForeignKey(
        null=True,
        to="goodnewsbot_worker.SubredditsToPostTo",
        on_delete=models.SET_NULL,
        related_name="source",
    )
    title_as_posted = models.CharField(
        null=True,
        max_length=300,
        verbose_name=(
            "Reddit Post Title (may need to have been shortened to fit "
            "Reddit's 300 char link post title limit)"
        ),
    )
    our_post_permalink = models.CharField(
        null=True,
        max_length=128,
    )

    def __str__(self):
        return f"{self.analysed_sentiment2} - {self.subreddit_posted_to}"


class RSSPost(SentimentAnalysis):
    """
    Model to store RSS news stories
    """
    title = models.CharField(max_length=512)
    story_body = models.TextField(null=True)
    story_url = models.URLField()

    def __str__(self):
        return f"{self.from_subreddit} - {self.title}"


class RedditPost(SentimentAnalysis):
    """
    Model to store Reddit posts
    """
    post_title = models.CharField(max_length=300)
    post_url = models.CharField(max_length=2000)
    from_subreddit = models.ForeignKey(
        on_delete=models.DO_NOTHING,
        to="goodnewsbot_worker.SubredditsToRead",
        related_name="reddit_post",
    )
    their_post_permalink = models.CharField(max_length=128)

    def __str__(self):
        return f"{self.post_title}"


class NewsPost(TimeStampedModel):
    """
    Model to store news posts and associated sentiment analysis data
    """
    SUBREDDIT_POSTED_TO = Choices(
        (0, "justbadnews", "JustBadNews"),
        (1, "justgoodnews", "JustGoodNews"),
    )

    post_title = models.CharField(max_length=300)
    post_url = models.CharField(max_length=2000)
    from_subreddit = models.ForeignKey(
        on_delete=models.DO_NOTHING,
        to="goodnewsbot_worker.SubredditsToRead",
    )
    permalink = models.CharField(max_length=128)
    analysed_sentiment2 = models.ForeignKey(
        to="goodnewsbot_worker.Sentiment",
        on_delete=models.DO_NOTHING,
        null=True,
    )
    quantified_positive = models.DecimalField(
        null=True,
        blank=True,
        max_digits=21,
        decimal_places=19,
    )
    quantified_negative = models.DecimalField(
        null=True,
        blank=True,
        max_digits=21,
        decimal_places=19,
    )
    quantified_neutral = models.DecimalField(
        null=True,
        blank=True,
        max_digits=21,
        decimal_places=19,
    )
    quantified_mixed = models.DecimalField(
        null=True,
        blank=True,
        max_digits=21,
        decimal_places=19,
    )
    posted_to = models.SmallIntegerField(
        null=True,
        blank=True,
        choices=SUBREDDIT_POSTED_TO,
    )

    def __str__(self):
        return f"{self.post_title} - {self.analysed_sentiment2}"
