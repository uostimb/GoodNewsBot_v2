import sys

import boto3
import praw
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from model_utils.models import TimeStampedModel

from goodnewsbot_worker.utils import clean_url, clean_title


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

    def get_new_posts(self):
        """
        Fetches posts for self.subreddit_name and populates RedditPost
        model
        """
        post_limit = self.post_limit
        subreddit_name = self.subreddit_name
        print(
            f"[{timezone.now()}] Fetching {post_limit} posts from "
            f"{subreddit_name}.",
        )
        new_posts_count = 0
        reddit = praw.Reddit()
        subreddit = reddit.subreddit(subreddit_name)

        existing_urls = set(
            SentimentAnalysis.objects.values_list("news_story_url", flat=True)
        )

        submissions = set()
        # we probably care about 'rising' posts [breaking news] more than
        # 'hot' posts, but if the subreddit doesn't have much activity or
        # traffic then 'rising' could be empty
        submissions.update(subreddit.rising(limit=post_limit))
        submissions.update(subreddit.hot(limit=post_limit))

        for submission in submissions:

            # ignore non-link posts
            if not submission.is_self:

                dirty_url = submission.url
                cleaned_url = clean_url(dirty_url)

                dirty_title = submission.title
                cleaned_title = clean_title(dirty_title)

                if not RedditPost.objects.post_values_ok(
                    cleaned_url,
                    cleaned_title,
                    subreddit_name,
                ):
                    # can't store post: let method print error and skip to next
                    continue

                if cleaned_url not in existing_urls:
                    try:
                        RedditPost.objects.create(
                            news_story_url=cleaned_url,
                            post_title=cleaned_title,
                            from_subreddit=self,
                            their_post_permalink=submission.permalink,
                        )
                        existing_urls.add(cleaned_url)
                        new_posts_count += 1

                    except Exception as e:
                        print(
                            f"[{timezone.now()}] ERROR! Cant write to DB! "
                            f"url: {cleaned_url}, "
                            f"title: {cleaned_title}, "
                            f"from subredditt: {subreddit_name}, "
                            f"error: {e} {sys.exc_info()}",
                        )

        return new_posts_count


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
        blank=True,
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
    news_story_url = models.URLField(max_length=2000)
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
    from_rss_feed = models.ForeignKey(
        on_delete=models.DO_NOTHING,
        to="goodnewsbot_worker.RSSToRead",
        related_name="reddit_post",
    )

    def __str__(self):
        return f"{self.from_rss_feed} - {self.title}"


class RedditPostManager(models.Manager):
    def post_values_ok(self, url, title, subreddit_name):
        max_url_len = self.model._meta.get_field("news_story_url").max_length
        max_title_len = self.model._meta.get_field("post_title").max_length

        if len(url) > max_url_len:
            print(
                f"[{timezone.now()}] "
                f"ERROR! Cant write post to DB - URL too long! "
                f"url: {url}, "
                f"title: {title}, "
                f"from subredditt: {subreddit_name}"
            )
            return False

        elif len(title) > max_title_len:
            print(
                f"[{timezone.now()}] "
                f"ERROR! Cant write post to DB - Title too long! "
                f"url: {url}, "
                f"title: {title}, "
                f"from subredditt: {subreddit_name}"
            )
            return False

        else:
            return True

    def get_new_posts(self):
        subreddits_to_read = SubredditsToRead.objects.active()
        for subreddit in subreddits_to_read:
            new_posts = subreddit.get_new_posts()
            print(
                f"[{timezone.now()}] Found {new_posts} new posts in "
                f"{subreddit.subreddit_name}.",
            )
            self.model.objects.analyse_new_posts()

    def analyse_new_posts(self):
        new_posts = (
            super()
            .get_queryset()
            .filter(analysed_sentiment2__isnull=True)
        )
        for post in new_posts:
            post.analyse_sentiment_and_repost()


class RedditPost(SentimentAnalysis):
    """
    Model to store Reddit posts
    """
    post_title = models.CharField(max_length=300)
    from_subreddit = models.ForeignKey(
        on_delete=models.DO_NOTHING,
        to="goodnewsbot_worker.SubredditsToRead",
        related_name="reddit_post",
    )
    their_post_permalink = models.CharField(max_length=128)

    objects = RedditPostManager()

    def __str__(self):
        return f"{self.post_title}"

    def analyse_sentiment_and_repost(self):
        """
        Send self.post_title to AWS for analysis and repost if above cut offs
        """
        aws_client = boto3.client("comprehend")
        response = aws_client.detect_sentiment(
            Text=self.post_title,
            LanguageCode="en",
        )

        response_metadata = response.get("ResponseMetadata")
        if not response_metadata.get("HTTPStatusCode") == 200:
            print(
                f"[{timezone.now()}] ERROR Analysing sentiment of "
                f"{self.post_title}! "
                f"response: {response}"
            )
        else:
            sentiment_response = response.get("Sentiment")
            sentiment = Sentiment.objects.get(sentiment=sentiment_response)
            self.analysed_sentiment2 = sentiment

            sentiment_score = response.get("SentimentScore")
            self.quantified_positive = sentiment_score.get("Positive")
            self.quantified_negative = sentiment_score.get("Negative")
            self.quantified_neutral = sentiment_score.get("Neutral")
            self.quantified_mixed = sentiment_score.get("Mixed")
            self.save()

            sentiment_obj = Sentiment.objects.filter(
                sentiment=self.analysed_sentiment2.sentiment,
            )

            if sentiment_obj:
                sentiment_obj = sentiment_obj.get()
                quantification = getattr(
                    self,
                    f"quantified_{sentiment_response.lower()}"
                )
                if quantification > sentiment_obj.cutoff:
                    self.post_to_reddit(sentiment_obj)

    def post_to_reddit(self, sentiment):
        if sentiment == Sentiment.objects.get(sentiment="POSITIVE"):
            adjective_str = "Positive"
            past_tense_str = "Positivity"
            quantification = round(self.quantified_positive, 3)
        elif sentiment == Sentiment.objects.get(sentiment="NEGATIVE"):
            adjective_str = "Negative"
            past_tense_str = "Negativity"
            quantification = round(self.quantified_negative, 3)
        else:
            print(
                f"[{timezone.now()}] "
                f"ERROR! Cannot handle Reddit Post Sentiment Type {sentiment}!"
                f" Post title: {self.post_title}, "
                f"from subredditt: {self.from_subreddit.subreddit_name}"
            )
            return

        if settings.DEBUG:
            subreddit = settings.TESTING_SUBREDDIT
        else:
            subreddit = sentiment.subreddit_to_post_to.subreddit_name

        print(
            f'[{timezone.now()}] Posting {adjective_str} post: '
            f'"{self.post_title}" to {subreddit}'
        )
        reddit = praw.Reddit()
        reddit_post = (
            reddit
            .subreddit(subreddit)
            .submit(
                title=self.post_title,
                url=self.news_story_url,
            )
        )
        reddit_post.mod.flair(
            text=f"{past_tense_str}={quantification}"
        )
        reddit_post.reply(
            f"xpost from r/{self.from_subreddit.subreddit_name}. "
            f"[original post]({self.their_post_permalink})"
        )
        self.subreddit_posted_to = sentiment.subreddit_to_post_to
        self.our_post_permalink = reddit_post.permalink
        self.title_as_posted = self.post_title
        self.save()
