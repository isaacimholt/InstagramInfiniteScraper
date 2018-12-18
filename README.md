[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

```python
from instagram_is import InstagramIS

after = '2018-12-02 17:00'  # utc
before = '2018-12-02 22:00' # utc
locations = [
    338173398,
    386067484,
    398631295,
    403070269,
    1024244801,
    270989023327664,
    412216912138139,
    1516734475005815,
    1965086357122989,
]

iis = InstagramIS()

top_posts = iis\
    .location_feed(locations)\
    .created_range(after, before)\
    .top(10, 'engagement', unique=True)\
    .save_csv('top_10_posts.csv')\
    .sort('created_at')

top_users = [p.owner_num_id for p in top_posts]

iis\
    .user_stream(top_users)\
    .top(5, 'followed_by_count', unique=True)\
    .to_csv('top_5_influencers.csv')

iis\
    .location_feed(locations)\
    .created_range(after, before)\
    .unique()\
    .to_csv('my_data.csv')

# todo
# get all posts from these locations
# will return a single stream of posts
# with posts ordered according to location, then feed
# e.g. <location 1 posts>, <location 2 posts>, etc
iis.location_feed(locations)\
   # this method filters posts according to creation date
   # however it is much more optimized than a regular filter
   # each location feed will terminate once the date range is exceeded
   # always try to filter items as soon as possible in stream
   # otherwise the entire feed(s) will be processed (long wait)
   # (each location feed is filtered individually in the muxer)
   .created_range(after, before)\
   # this is an optimized method that reduces memory usage
   .top(10, 'engagement', unique=True)\
   # as stream is running, saves items to csv
   .save_csv('top_10_posts.csv')\
   # convert stream of posts into stream of users
   # (user streams are muxed)
   .owner_stream()\
   # get top 5 users
   .top(5, 'followed_by_count', unique=True)\
   # save users to csv
   .save_csv('top_5_influencers.csv')\
   # get a stream of the posts for each user
   # stream contents are again <user 1 posts>, <user 2 posts>, etc
   # (post streams are muxed)
   .post_stream()\
   # return posts from last 7 days, up to 10 per user
   # (filter is applied to each muxed stream individually)
   .recent(days=7)\
   # limit each muxed user stream
   # (filter is applied to each muxed stream individually)
   .limit_each(10)\
   # save posts to csv
   .save_csv('top_influencers_recent_posts.csvs')\
   # convert stream of posts to stream of comments per post
   .comment_stream()\
   # max 100 total comments
   # (because of the 'chained' nature of element ordering, it's possible
   #  the limit will trigger before getting results from each post)
   .limit(100)\
   # save comments to csv
   .save_csv('top_influencers_recent_comments.csv')\
   # actually execute the stream
   .run()

```