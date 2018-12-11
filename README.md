```python
import pendulum
from instagram_is import InstagramIS

begin = '2018-12-02 17:00'
begin = pendulum.datetime(2018, 12, 2, 18, tz='Europe/Rome').in_tz('UTC')
end = '2018-12-02 22:00'
end = pendulum.datetime(2018, 12, 2, 23, tz='Europe/Rome').in_tz('UTC')
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

InstagramIS\
    .location_feed(locations)\
    .date_range(begin, end)\
    .to_csv('my_data.csv')
```