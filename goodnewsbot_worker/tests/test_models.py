from django.test import TestCase
from model_mommy import mommy

from goodnewsbot_worker.models import RedditPost, SubredditsToRead, Sentiment


class TestModels(TestCase):
    """
    GoodNewsBot_worker model tests
    N.B. SentimentAnalysis model is subclassed by RedditPost and RSSPost models
    """

    def setUp(self):
        self.test_subreddit_to_post_to = mommy.make(
            "goodnewsbot_worker.SubredditsToPostTo",
            subreddit_name="JustGoodTesting",
        )

    def test_subredditstoread_model(self):
        test_subreddit = "JustGoodNews"
        test_post_limit = 5

        model_obj = mommy.make(
            "goodnewsbot_worker.SubredditsToRead",
            subreddit_name=test_subreddit,
            post_limit=5,
        )

        self.assertEqual(
            model_obj.__str__(),
            f"{test_subreddit} ({test_post_limit} posts)",
        )

        self.assertIn(
            model_obj.pk,
            SubredditsToRead.objects.active().values_list("pk", flat=True),
        )

        model_obj.disabled = True
        model_obj.save()

        self.assertEqual(
            model_obj.__str__(),
            f"{test_subreddit} ({test_post_limit} posts) [DISABLED]",
        )

        self.assertNotIn(
            model_obj.pk,
            SubredditsToRead.objects.active().values_list("pk", flat=True),
        )

        num_new_posts = model_obj.get_new_posts()

        self.assertGreater(
            num_new_posts,
            1,
            msg=(
                f"Did not get any posts with 'new' urls from {test_subreddit} "
                "subreddit!"
            ),
        )

    def test_subredditstopostto_model(self):
        self.assertEqual(
            self.test_subreddit_to_post_to.__str__(),
            self.test_subreddit_to_post_to.subreddit_name,
        )

    def test_sentiment_model(self):
        sentiment_name = "SENTIMENT"
        cutoff = 0.75555
        model_obj = mommy.make(
            "goodnewsbot_worker.Sentiment",
            sentiment=sentiment_name,
            cutoff=cutoff,
        )
        self.assertEqual(
            model_obj.__str__(),
            f"{sentiment_name} (>{cutoff})"
        )

    def test_redditpost_model(self):
        positive_post_title = (
            "This incredible post title is the most positive thing I've "
            "ever experienced in my life!  It is honestly the best thing "
            "in the world and I love it! Good, great, fantastic and "
            "amazing are just some descriptions of it!"
        )
        negative_post_title = (
            "This terrible post title is the worst things I've ever "
            "experienced in my life!  It is honestly the most disappointing "
            "thing in the world and I hate it!  Awful, horrible, abysmal and "
            "disastrous are just some descriptions of it!"
        )

        pos_post_object = mommy.make(
            "goodnewsbot_worker.RedditPost",
            post_title=positive_post_title,
        )

        neg_post_object = mommy.make(
            "goodnewsbot_worker.RedditPost",
            post_title=negative_post_title,
        )

        self.assertEqual(
            pos_post_object.__str__(),
            positive_post_title,
        )

        # Set all Sentiments to post to our testing Subreddit
        Sentiment.objects.update(
            subreddit_to_post_to=self.test_subreddit_to_post_to,
        )

        positive_sentiment = Sentiment.objects.get(sentiment="POSITIVE")
        negative_sentiment = Sentiment.objects.get(sentiment="NEGATIVE")

        self.assertIsNone(pos_post_object.analysed_sentiment2)
        self.assertIsNone(neg_post_object.analysed_sentiment2)

        pos_post_object.analyse_sentiment_and_repost()
        neg_post_object.analyse_sentiment_and_repost()

        # 'POSITIVE' post checks
        self.assertEqual(
            pos_post_object.analysed_sentiment2,
            positive_sentiment,
        )

        self.assertGreater(
            pos_post_object.quantified_positive,
            pos_post_object.quantified_negative,
        )

        # 'NEGATIVE' post checks
        self.assertEqual(
            neg_post_object.analysed_sentiment2,
            negative_sentiment,
        )

        self.assertGreater(
            neg_post_object.quantified_negative,
            neg_post_object.quantified_positive,
        )

        # Generic 'posted' post checks
        self.assertEqual(
            pos_post_object.subreddit_posted_to,
            self.test_subreddit_to_post_to,
        )

        self.assertIsNotNone(pos_post_object.our_post_permalink)

        self.assertEqual(
            pos_post_object.post_title,
            pos_post_object.title_as_posted,
        )

    def test_redditpostmanager_post_values_ok(self):
        reddit_post = mommy.make("goodnewsbot_worker.RedditPost")
        good_title = reddit_post.post_title
        good_url = reddit_post.news_story_url

        self.assertTrue(
            RedditPost.objects.post_values_ok(
                url=good_url,
                title=good_title,
                subreddit_name="JustGoodTesting",
            )
        )

        max_title_length = (
            RedditPost
            ._meta
            .get_field("post_title")
            .max_length
        )

        invalid_title = ""
        for i in range(max_title_length + 1):
            invalid_title += "A"

        max_url_length = (
            RedditPost
            ._meta
            .get_field("news_story_url")
            .max_length
        )

        invalid_url = ""
        for i in range(max_url_length + 1):
            invalid_url += "A"

        self.assertFalse(
            RedditPost.objects.post_values_ok(
                url=good_url,
                title=invalid_title,
                subreddit_name="JustGoodTesting",
            )
        )

        self.assertFalse(
            RedditPost.objects.post_values_ok(
                url=invalid_url,
                title=good_title,
                subreddit_name="JustGoodTesting",
            )
        )

        self.assertFalse(
            RedditPost.objects.post_values_ok(
                url=invalid_url,
                title=invalid_title,
                subreddit_name="JustGoodTesting",
            )
        )
