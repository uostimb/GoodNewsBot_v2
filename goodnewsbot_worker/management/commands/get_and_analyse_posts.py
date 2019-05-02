from django.core.management.base import BaseCommand
from django.utils import timezone

from goodnewsbot_worker.models import RedditPost


class Command(BaseCommand):
    """
    To be invoked (hourly?) by cron similar to the following
    pseudo-command:

        0 * * * * \
            . bin/activate && \
            cd dev/goodnewsbot && \
            bin/python dev/goodnewsbot/manage.py get_and_analyse_posts \
                >> dev/goodnewsbot/goodnewsbot.log 2>&1
    """
    help = (
        "Fetch and analyse posts from reddit, repost +ve and -ve news stories"
    )

    def handle(self, **options):
        RedditPost.objects.get_new_posts()
        self.stdout.write(f"[{timezone.now()}] Done!")
