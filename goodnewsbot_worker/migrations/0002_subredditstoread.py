# Generated by Django 2.2 on 2019-04-11 02:48

from django.db import migrations, models
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ('goodnewsbot_worker', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubredditsToRead',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('subreddit_name', models.CharField(max_length=32)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
