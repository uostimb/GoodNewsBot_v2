import boto3
import praw
import time
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from goodnewsbot_worker.models import SubredditsToRead, NewsPost
from goodnewsbot_worker.utils import nat_join, clean_url, clean_title


class Command(BaseCommand):
    """
    To be invoked daily by cron similar to the following
    pseudo-command:

        30 8 * * 1-5 \
            . bin/activate && \
            cd empirical/empirical && \
            bin/python empirical/empirical/manage.py \
                reminder_overdue \
                --settings=empirical.settings.production > \
                empirical/empirical/logs/cron_reminder_overdue.log \
                2>&1
    """
    help = (
        'Sends a summary email detailing overdue'
        ' `InstructionReminder`s.'
    )

    def handle(self, **options):
        to_read = SubredditsToRead.get_active.all()

        to_read_list = to_read.values_list('subreddit_name', flat=True)
        to_read_list = nat_join(to_read_list)

        self.stdout.write(
            f'[{timezone.now()}] Fetching Reddit Posts from {to_read_list}.',
        )

        reddit = praw.Reddit()

        new_posts = []

        for subreddit_to_read in to_read:
            post_limit = subreddit_to_read.post_limit
            self.stdout.write(
                f"[{timezone.now()}] Fetching {post_limit} posts from "
                f"{subreddit_to_read.subreddit_name}.",
            )

            subreddit_count = 0

            subreddit = reddit.subreddit(subreddit_to_read.subreddit_name)
            for submission in subreddit.hot(limit=post_limit):

                dirty_url = submission.url
                cleaned_url = clean_url(dirty_url)

                dirty_title = submission.title
                cleaned_title = clean_title(dirty_title)

                if not NewsPost.objects.filter(post_url=cleaned_url).exists():
                    try:
                        new_post = NewsPost.objects.create(
                            post_url=cleaned_url,
                            post_title=cleaned_title,
                            from_subreddit=subreddit_to_read,
                        )
                        new_posts.append(new_post)

                        subreddit_count += 1
                    except:
                        self.stdout.write(
                            f"[{timezone.now()}] ERROR!  Cant write to DB: "
                            f"url: {cleaned_url}, title: {cleaned_title}, "
                            f"from subredditt {subreddit_to_read}",
                        )

            self.stdout.write(
                f"[{timezone.now()}] Found {subreddit_count} new posts in "
                f"{subreddit_to_read.subreddit_name}.",
            )

        if not len(new_posts):
            self.stdout.write(
                f'[{timezone.now()}] No New Posts Found! exiting.',
            )
            return
        else:
            self.stdout.write(
                f'[{timezone.now()}] Analysing sentiment of {len(new_posts)} '
                f'new posts.',
            )

            aws_client = boto3.client('comprehend')
            positive_posts = []
            negative_posts = []

            for post in new_posts:

                response = aws_client.detect_sentiment(
                    Text=post.post_title,
                    LanguageCode='en',
                )

                if response.get('ResponseMetadata').get('HTTPStatusCode') == 200:
                    post.analysed_sentiment = response.get('Sentiment')
                    post.quantified_positive = response.get("SentimentScore").get('Positive')
                    post.quantified_negative = response.get("SentimentScore").get('Negative')
                    post.quantified_neutral = response.get("SentimentScore").get('Neutral')
                    post.quantified_mixed = response.get("SentimentScore").get('Mixed')
                    post.save()
                else:
                    self.stdout.write(
                        f'[{timezone.now()}] ERROR Analysing sentiment of {post.post_title}'
                    )

                if response.get("SentimentScore").get('Positive') > 0.7:
                    positive_posts.append(post)
                elif response.get("SentimentScore").get('Negative') > 0.7:
                    negative_posts.append(post)

            if positive_posts:
                self.stdout.write(f'[{timezone.now()}] Found {len(positive_posts)} Positive posts!')
                for post in positive_posts:

                    post.posted_to = NewsPost.SUBREDDIT_POSTED_TO.justgoodnews
                    post.save()

                    reddit_post = (
                        reddit
                        .subreddit(settings.SUBREDDIT_TO_WRITE_GOOD)
                        .submit(
                            title=post.post_title,
                            url=post.post_url,
                        )
                    )
                    reddit_post.mod.flair(
                        text=f"Positivity={post.quantified_positive}",
                    )

                    # Reddit API limited to 60 requests per minute
                    time.sleep(1)

            if negative_posts:
                self.stdout.write(f'[{timezone.now()}] Found {len(negative_posts)} Negative posts!')
                for post in negative_posts:

                    post.posted_to = NewsPost.SUBREDDIT_POSTED_TO.justbadnews
                    post.save()

                    reddit_post = (
                        reddit
                        .subreddit(settings.SUBREDDIT_TO_WRITE_BAD)
                        .submit(
                            title=post.post_title,
                            url=post.post_url,
                        )
                    )
                    reddit_post.mod.flair(
                        text=f"Negativity={post.quantified_negative}",
                    )

                    # Reddit API limited to 60 requests per minute
                    time.sleep(1)

            self.stdout.write(f'[{timezone.now()}] Done!')
