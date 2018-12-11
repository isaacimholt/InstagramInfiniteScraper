```python
import pendulum
from instagram_is import InstagramIS

begin = pendulum.datetime(2018, 12, 2, 18, tz='Europe/Rome').in_tz('UTC')
end = pendulum.datetime(2018, 12, 2, 23, tz='Europe/Rome').in_tz('UTC')

likes = InstagramIS\
    .tag_feed('stadioolimpico')\
    .filter_date_created(begin, end)\
    .limit(100)\
    .to_list(sort='like_count')
```