from backoff import on_exception, expo
from instagram_web_api import Client
from instagram_web_api.errors import ClientError
from ratelimit import limits, RateLimitException


class CustomWebApiClient(Client):
    """
    Patch to rate-limit & retry connections to instagram.
    Limit calls to 1 per 1.2 seconds. If this is exceeded RateLimitException is thrown.
    When RateLimitException is thrown, retry with an exponential backoff + jitter,
    up to 3 mins before giving up and raising the error.
    This was done to try and put some random wait times between calls to instagram so
    all calls are not so rapid and evenly spaced.
    When ClientError is thrown it usually means instagram is throttling us, so retry with
    exponential backoff + jitter up to 15 mins total wait time before giving up.
    """

    @on_exception(expo, ClientError, max_time=60 * 15)
    @on_exception(expo, RateLimitException, max_time=60 * 3)
    @limits(calls=1, period=1.2)
    def _make_request(self, *args, **kwargs):
        return super()._make_request(*args, **kwargs)
