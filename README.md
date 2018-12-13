```python
from instagram_is import instagram_is

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

top_posts = instagram_is\
    .location_feed(locations)\
    .date_range(after, before)\
    .top(10, 'engagement', unique=True)\
    .to_list(sort='created_at')

top_users = [p.owner_num_id for p in top_posts]

instagram_is\
    .user_stream(top_users)\
    .top(5, 'followed_by_count', unique=True)\
    .to_csv('top_influencers.csv')

instagram_is\
    .location_feed(locations)\
    .date_range(after, before)\
    .unique()\
    .to_csv('my_data.csv')
```