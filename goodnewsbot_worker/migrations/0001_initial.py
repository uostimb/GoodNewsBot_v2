# Generated by Django 2.2 on 2019-04-11 02:38

from django.db import migrations, models
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='NewsPost',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('post_title', models.CharField(max_length=300)),
                ('post_url', models.CharField(max_length=300)),
                ('from_subreddit', models.CharField(max_length=32)),
                ('analysed_sentiment', models.CharField(blank=True, max_length=8, null=True)),
                ('quantified_positive', models.DecimalField(blank=True, decimal_places=19, max_digits=21, null=True)),
                ('quantified_negative', models.DecimalField(blank=True, decimal_places=19, max_digits=21, null=True)),
                ('quantified_neutral', models.DecimalField(blank=True, decimal_places=19, max_digits=21, null=True)),
                ('quantified_mixed', models.DecimalField(blank=True, decimal_places=19, max_digits=21, null=True)),
                ('posted_to', models.SmallIntegerField(blank=True, choices=[(0, 'JustBadNews'), (1, 'JustGoodNews')], null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
