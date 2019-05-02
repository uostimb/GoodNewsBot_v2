# Generated by Django 2.2 on 2019-05-02 14:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('goodnewsbot_worker', '0012_populate_new_news_story_url_field'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='redditpost',
            name='post_url',
        ),
        migrations.RemoveField(
            model_name='rsspost',
            name='story_url',
        ),
        migrations.AddField(
            model_name='rsspost',
            name='from_rss_feed',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.DO_NOTHING, related_name='reddit_post', to='goodnewsbot_worker.RSSToRead'),
            preserve_default=False,
        ),
    ]
