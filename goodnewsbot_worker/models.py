import feedparser
import sys

import boto3
import praw
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone
from model_utils.models import TimeStampedModel

from goodnewsbot_worker.utils import clean_url, clean_title, clean_description


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
                            title_as_posted=cleaned_title,
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
    title = models.CharField(max_length=256, editable=False)
    description = models.CharField(max_length=1024, null=True, editable=False)
    can_handle_https_story_urls = models.BooleanField(
        default=True,
        verbose_name=(
            "Should we prepend https:// to this news source's story urls?"
        ),
    )
    disabled = models.BooleanField(default=False)

    objects = SourceToReadManager()

    def __str__(self):
        ret = f"{self.title} - {self.url}"
        if self.disabled:
            ret += " [DISABLED]"
        return ret

    def save(self, *args, **kwargs):
        """If new RSS entry attempt to parse RSS to get feed title and desc"""
        if not self.pk:
            feed = feedparser.parse(self.url)
            self.title = feed.feed.title
            self.description = feed.feed.description
        super().save(*args, **kwargs)

    def get_new_stories(self):
        """
        Fetches stories for feed at self.url and populates RSSPost
        model
        """
        url = self.url
        print(
            f'[{timezone.now()}] Fetching stories from "{self.title}" at {url}'
        )
        new_stories_count = 0
        existing_urls = set(
            SentimentAnalysis.objects.values_list("news_story_url", flat=True)
        )
        feed = feedparser.parse(self.url)
        for entry in feed.entries:

            title = entry.title
            description = clean_description(entry.description)
            story_url = clean_url(entry.guid)

            if not RSSPost.objects.post_values_ok(story_url, title, description, self):
                # can't store story: let method print error and skip to next
                continue

            if story_url not in existing_urls:
                try:
                    RSSPost.objects.create(
                        title=title,
                        description=description,
                        news_story_url=story_url,
                        from_rss_feed=self,
                    )
                    existing_urls.add(story_url)
                    new_stories_count += 1

                except Exception as e:
                    print(
                        f"[{timezone.now()}] ERROR! Cant write to DB! "
                        f"url: {story_url}, "
                        f"title: {title}, "
                        f"description: {description}, "
                        f"from RSS: {self}, "
                        f"error: {e} {sys.exc_info()}",
                    )

        return new_stories_count


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

    def post_to_reddit(self, sentiment, xpost_details=None, https=False):

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
                f"[{timezone.now()}] ERROR! Cannot handle Reddit Post "
                f"Sentiment Type {sentiment}!"
            )
            return

        if settings.DEBUG:
            subreddit = settings.TESTING_SUBREDDIT
        else:
            subreddit = sentiment.subreddit_to_post_to.subreddit_name

        print(
            f'[{timezone.now()}] Posting {adjective_str} post: '
            f'"{self.title_as_posted}" to {subreddit}'
        )

        url = self.news_story_url
        if https:
            url = f"https://{url}"

        reddit = praw.Reddit()
        reddit_post = (
            reddit
            .subreddit(subreddit)
            .submit(
                title=self.title_as_posted,
                url=url,
            )
        )
        reddit_post.mod.flair(
            text=f"{past_tense_str}={quantification}"
        )

        if xpost_details:
            xpost_from = xpost_details['from_subreddit']
            xpost_permalink = xpost_details['their_permalink']
            # reply to submission with "xpost" comment
            reddit_post.reply(
                f"xpost from r/{xpost_from}. "
                f"[original post]({xpost_permalink})"
            )

        self.subreddit_posted_to = sentiment.subreddit_to_post_to
        self.our_post_permalink = reddit_post.permalink
        self.save()


class RSSPostManager(models.Manager):
    def post_values_ok(self, url, title, description, rss):
        meta = self.model._meta
        max_url_len = meta.get_field("news_story_url").max_length
        max_title_len = meta.get_field("title").max_length
        max_description_len = meta.get_field("description").max_length

        if len(url) > max_url_len:
            print(
                f"[{timezone.now()}] "
                f"ERROR! Cant write post to DB - URL too long! "
                f"url: {url}, "
                f"title: {title}, "
                f"from RSS: {rss}"
            )
            return False

        elif len(title) > max_title_len:
            print(
                f"[{timezone.now()}] "
                f"ERROR! Cant write post to DB - Title too long! "
                f"url: {url}, "
                f"title: {title}, "
                f"from RSS: {rss}"
            )
            return False

        elif len(description) > max_description_len:
            print(
                f"[{timezone.now()}] "
                f"ERROR! Cant write post to DB - Description too long! "
                f"url: {url}, "
                f"title: {title}, "
                f"description: {description}, "
                f"from RSS: {rss}"
            )
            return False

        else:
            return True

    def get_new_posts(self):
        rss_to_read = RSSToRead.objects.active()
        for rss in rss_to_read:
            new_story_count = rss.get_new_stories()
            print(
                f"[{timezone.now()}] Found {new_story_count} new stories in "
                f"{rss}.",
            )
        self.model.objects.analyse_new_posts()

    def analyse_new_posts(self):
        new_stories = (
            super()
            .get_queryset()
            .filter(analysed_sentiment2__isnull=True)
        )
        for story in new_stories:
            story.analyse_sentiment_and_repost()


class RSSPost(SentimentAnalysis):
    """
    Model to store RSS news stories
    """
    title = models.CharField(max_length=512)
    description = models.CharField(max_length=512, null=True)
    story_body = models.TextField(null=True)
    from_rss_feed = models.ForeignKey(
        on_delete=models.DO_NOTHING,
        to="goodnewsbot_worker.RSSToRead",
        related_name="reddit_post",
    )
    title_analysis = JSONField(null=True, blank=True)
    description_analysis = JSONField(null=True, blank=True)

    objects = RSSPostManager()

    def __str__(self):
        return f"{self.from_rss_feed} - {self.title}"

    def analyse_sentiment_and_repost(self):
        """
        if (len(self.title) + len(self.description)) <= 300 send combination
        to AWS for analysis. Also send title and description individually.
        Post to Reddit if quantification above sentiment cut off
        """
        if len(self.title) + len(self.description) <= 298:
            self.title_as_posted = f"{self.title}. {self.description}"
        else:
            # ToDo:  When combination is too long, consider setting whether we
            #  should use title or description for that feed on RSSToRead model
            # defaulting to description since it tends to be more descriptive!
            self.title_as_posted = self.description[:300]
        self.save()

        aws_client = boto3.client("comprehend")
        response = aws_client.detect_sentiment(
            Text=self.title_as_posted,
            LanguageCode="en",
        )

        response_metadata = response.get("ResponseMetadata")
        if not response_metadata.get("HTTPStatusCode") == 200:
            print(
                f"[{timezone.now()}] ERROR Analysing sentiment of "
                f"{self.title_as_posted}! "
                f"response: {response}"
            )
            return

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
                xpost_details = None
                https = self.from_rss_feed.can_handle_https_story_urls
                self.post_to_reddit(sentiment_obj, xpost_details, https)

        # also test title and description independently for future statistical
        # analysis to determine if either gives more accurate results than the
        # other or the concatenation
        title_analysis = aws_client.detect_sentiment(
            Text=self.title,
            LanguageCode="en",
        )
        response_metadata = title_analysis.get("ResponseMetadata")
        if not response_metadata.get("HTTPStatusCode") == 200:
            print(
                f"[{timezone.now()}] ERROR Analysing sentiment of "
                f"{self.title}! "
                f"response: {response}"
            )
        else:
            sentiment_score = title_analysis.get("SentimentScore")
            title_analysis_dict = {
                "analysed_sentiment2": title_analysis.get("Sentiment"),
                "quantified_positive": sentiment_score.get("Positive"),
                "quantified_negative": sentiment_score.get("Negative"),
                "quantified_neutral": sentiment_score.get("Neutral"),
                "quantified_mixed": sentiment_score.get("Mixed"),
            }
            self.title_analysis = title_analysis_dict

        if not self.title_as_posted == self.description:
            description_analysis = aws_client.detect_sentiment(
                Text=self.description,
                LanguageCode="en",
            )
            response_metadata = description_analysis.get("ResponseMetadata")
            if not response_metadata.get("HTTPStatusCode") == 200:
                print(
                    f"[{timezone.now()}] ERROR Analysing sentiment of "
                    f"{self.description}! "
                    f"response: {response}"
                )
            else:
                sentiment_score = description_analysis.get("SentimentScore")
                description_analysis_dict = {
                    "analysed_sentiment2": description_analysis.get("Sentiment"),
                    "quantified_positive": sentiment_score.get("Positive"),
                    "quantified_negative": sentiment_score.get("Negative"),
                    "quantified_neutral": sentiment_score.get("Neutral"),
                    "quantified_mixed": sentiment_score.get("Mixed"),
                }
                self.description_analysis = description_analysis_dict

        self.save()


class RedditPostManager(models.Manager):
    def post_values_ok(self, url, title, subreddit_name):
        meta = self.model._meta
        max_url_len = meta.get_field("news_story_url").max_length
        max_title_len = meta.get_field("post_title").max_length

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
                    xpost_details = {
                        "from_subreddit": self.from_subreddit.subreddit_name,
                        "their_permalink": self.their_post_permalink,
                    }
                    self.post_to_reddit(sentiment_obj, xpost_details)
