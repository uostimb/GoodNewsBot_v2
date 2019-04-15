from django.db import models
from model_utils.choices import Choices
from model_utils.models import TimeStampedModel


class SubredditsToReadManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(disabled=False)


class SubredditsToRead(TimeStampedModel):
    """Model to store subreddits to fetch news posts from"""
    subreddit_name = models.CharField(
        max_length=32,
    )
    post_limit = models.IntegerField()
    disabled = models.BooleanField(default=False)

    objects = models.Manager()
    get_active = SubredditsToReadManager()

    def __str__(self):
        ret_str = f"{self.subreddit_name} ({self.post_limit} posts)"
        if self.disabled:
            ret_str += " [DISABLED]"
        return ret_str


class NewsPost(TimeStampedModel):
    """
    Model to store news posts and associated sentiment analysis data
    """
    SUBREDDIT_POSTED_TO = Choices(
        (0, "justbadnews", "JustBadNews"),
        (1, "justgoodnews", "JustGoodNews"),
    )

    post_title = models.CharField(
        max_length=300,
    )
    post_url = models.CharField(
        max_length=2000,
    )
    from_subreddit = models.ForeignKey(
        on_delete=models.DO_NOTHING,
        to="goodnewsbot_worker.SubredditsToRead",
        related_name="news_post",
    )
    permalink = models.CharField(
        max_length=128,
    )
    analysed_sentiment = models.CharField(
        null=True,
        blank=True,
        max_length=8,
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
        return f"{self.post_title} - {self.analysed_sentiment}"
