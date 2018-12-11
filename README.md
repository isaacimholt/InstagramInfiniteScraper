```python
import pendulum
from instagram_is import InstagramIS

begin = pendulum.datetime(2018, 12, 2, 18, tz='Europe/Rome').in_tz('UTC')
end = pendulum.datetime(2018, 12, 2, 23, tz='Europe/Rome').in_tz('UTC')

InstagramIS\
    .location_feed(
        338173398,
        386067484,
        398631295,
        403070269,
        1024244801,
        270989023327664,
        412216912138139,
        1516734475005815,
        1965086357122989,)\
    .date_range(begin, end)\
    .to_csv('my_data.csv')
```