## General:
- Use logging instead of calls to print()

## Cut out the middle man
- Start parsing news websites directly (using beautiful soup?)
- Summarise page contents use NLTK (https://stackabuse.com/text-summarization-with-nltk-in-python/)
ideally down to one or two 300 char blocks to minimise AWS sentiment analysis costs
- Hash summary and check hash rather than urls to see if we've seen the page contents before,
since (at least the BBC) initially post a tiny summary for important stories, then later update
with more content as it becomes available that might change sentiment?
- If find new hash of page contents and have already posted url, remove old post or just update
positivity / negativity flair?
- Compare sentiment of headlines to page content, see if it's worth parsing page contents in long term

- Analyse sentence (first / last) seperately, see if first is more valuable?

## Web front end
- Pages & filters / tables to search for urls / stores etc.
- Add new news sources (subreddits / news websites etc.)
    - If news website, what html tags or params are required to differentiate
    headlines / bylines / content
- Analytics:
    - Sentiment stats (e.g. total pos / neg) Change global pos / neg limits?
    - Sentment stats by source etc.  Change pos / neg limits by source?
    - Word cloud by source?
