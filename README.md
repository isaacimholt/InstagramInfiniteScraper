```python
from instagram_is import InstagramIS
InstagramIS\
    .tag_feed('stadioolimpico')\
    .filter_created(pendulum.datetime(2018, 12, 2, 18, tz='Europe/Rome').in_tz('UTC'),
                    pendulum.datetime(2018, 12, 2, 23, tz='Europe/Rome').in_tz('UTC'))\
    .to_set()
```