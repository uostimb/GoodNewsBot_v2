# Generated by Django 2.2 on 2019-05-06 19:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('goodnewsbot_worker', '0013_move_news_url_field_to_sentiment_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='rsstoread',
            name='description',
            field=models.CharField(editable=False, max_length=1024, null=True),
        ),
        migrations.AddField(
            model_name='rsstoread',
            name='title',
            field=models.CharField(default='Test', editable=False, max_length=256),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='sentiment',
            name='subreddit_to_post_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sentiment', to='goodnewsbot_worker.SubredditsToPostTo'),
        ),
    ]
