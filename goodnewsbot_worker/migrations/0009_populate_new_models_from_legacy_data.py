# Generated by Django 2.2 on 2019-05-02 10:58

from django.db import migrations


legacy_subreddits_posted_to = {
    0: "JustBadNews",
    1: "JustGoodNews",
}


def populate_new_subreddits_to_post_to_models(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    new_reddit_post_model = apps.get_model('goodnewsbot_worker', 'SubredditsToPostTo')
    new_reddit_post_model.objects.using(db_alias).create(subreddit_name="JustGoodNews")
    new_reddit_post_model.objects.using(db_alias).create(subreddit_name="JustBadNews")


def populate_new_sentiment_subreddit_to_post_to_field(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    new_reddit_post_model = apps.get_model('goodnewsbot_worker', 'SubredditsToPostTo')
    justgoodnews = new_reddit_post_model.objects.using(db_alias).get(subreddit_name="JustGoodNews")
    justbadnews = new_reddit_post_model.objects.using(db_alias).get(subreddit_name="JustBadNews")
    sentiment_model = apps.get_model('goodnewsbot_worker', 'Sentiment')
    (
        sentiment_model.objects.using(db_alias)
        .filter(sentiment="POSITIVE")
        .update(subreddit_to_post_to=justgoodnews)
    )
    (
        sentiment_model.objects.using(db_alias)
        .filter(sentiment="NEGATIVE")
        .update(subreddit_to_post_to=justbadnews)
    )


def populate_new_reddit_post_model(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    subreddit_to_post_to_model = apps.get_model('goodnewsbot_worker', 'SubredditsToPostTo')
    new_reddit_post_model = apps.get_model('goodnewsbot_worker', 'RedditPost')
    old_news_model = apps.get_model('goodnewsbot_worker', 'NewsPost')
    for news_post in old_news_model.objects.using(db_alias).all():
        if news_post.posted_to:
            posted_to_string = legacy_subreddits_posted_to[news_post.posted_to]
            posted_to = (
                subreddit_to_post_to_model.objects.using(db_alias)
                .get(subreddit_name=posted_to_string)
            )
        else:
            posted_to = None
        new_reddit_post_model.objects.using(db_alias).create(
            post_title=news_post.post_title,
            post_url=news_post.post_url,
            from_subreddit=news_post.from_subreddit,
            their_post_permalink=news_post.permalink,
            analysed_sentiment2=news_post.analysed_sentiment2,
            quantified_positive=news_post.quantified_positive,
            quantified_negative=news_post.quantified_negative,
            quantified_neutral=news_post.quantified_neutral,
            quantified_mixed=news_post.quantified_mixed,
            subreddit_posted_to=posted_to,
            title_as_posted=news_post.post_title,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('goodnewsbot_worker', '0008_new_models_for_getting_analysing_and_posting_news'),
    ]

    operations = [
        migrations.RunPython(
            populate_new_subreddits_to_post_to_models,
            migrations.RunPython.noop,
            atomic=True,
            elidable=True,
        ),
        migrations.RunPython(
            populate_new_sentiment_subreddit_to_post_to_field,
            migrations.RunPython.noop,
            atomic=True,
            elidable=True,
        ),
        migrations.RunPython(
            populate_new_reddit_post_model,
            migrations.RunPython.noop,
            atomic=True,
            elidable=True,
        ),
    ]