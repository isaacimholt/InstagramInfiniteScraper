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
    .to_list(sort='created_at')

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
```