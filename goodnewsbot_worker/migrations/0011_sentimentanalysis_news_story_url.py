# Generated by Django 2.2 on 2019-05-02 13:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('goodnewsbot_worker', '0010_delete_newspost'),
    ]

    operations = [
        migrations.AddField(
            model_name='sentimentanalysis',
            name='news_story_url',
            field=models.URLField(default='http://fakeurl.com', max_length=2000),
            preserve_default=False,
        ),
    ]