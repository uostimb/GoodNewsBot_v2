# Generated by Django 2.2 on 2019-05-02 12:58

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('goodnewsbot_worker', '0009_populate_new_models_from_legacy_data'),
    ]

    operations = [
        migrations.DeleteModel(
            name='NewsPost',
        ),
    ]