from django.contrib import admin

from goodnewsbot_worker import models


class SubredditsToReadAdmin(admin.ModelAdmin):
    list_display = ("subreddit_name", "post_limit", "disabled")
    list_filter = ["subreddit_name", "disabled"]
    search_fields = ["subreddit_name"]


admin.site.register(models.SubredditsToRead, SubredditsToReadAdmin)


class RSSToReadAdmin(admin.ModelAdmin):
    list_display = ("url", "disabled")
    list_filter = ["url", "disabled"]
    search_fields = ["url", "disabled"]


admin.site.register(models.RSSToRead, RSSToReadAdmin)


class SubredditsToPostToAdmin(admin.ModelAdmin):
    list_display = ("subreddit_name", )
    list_filter = ["subreddit_name"]
    search_fields = ["subreddit_name"]


admin.site.register(models.SubredditsToPostTo, SubredditsToPostToAdmin)


class SentimentAdmin(admin.ModelAdmin):
    list_display = ("sentiment", "cutoff", "subreddit_to_post_to")
    list_filter = ["sentiment", "cutoff", "subreddit_to_post_to"]
    search_fields = ["sentiment", "cutoff", "subreddit_to_post_to__subreddit_name"]


admin.site.register(models.Sentiment, SentimentAdmin)


class RSSPostAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "title_as_posted",
        "from_rss_feed",
        "analysed_sentiment2",
        "subreddit_posted_to",
    )
    list_filter = [
        "from_rss_feed",
        "analysed_sentiment2",
        "subreddit_posted_to",
    ]
    search_fields = [
        "title_as_posted",
        "from_rss_feed__url",
        "analysed_sentiment2__sentiment",
        "subreddit_posted_to__subreddit_name",
        "story_body"
    ]


admin.site.register(models.RSSPost, RSSPostAdmin)


class RedditPostAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "title_as_posted",
        "from_subreddit",
        "analysed_sentiment2",
        "subreddit_posted_to",
    )
    list_filter = [
        "from_subreddit",
        "analysed_sentiment2",
        "subreddit_posted_to",
    ]
    search_fields = [
        "title_as_posted",
        "from_subreddit__subreddit_name",
        "analysed_sentiment2__sentiment",
        "subreddit_posted_to__subreddit_name",
    ]


admin.site.register(models.RedditPost, RedditPostAdmin)
