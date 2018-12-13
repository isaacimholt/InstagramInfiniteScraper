import re
from collections import abc
from datetime import datetime
from typing import Iterator, Any, Optional, Callable, Sequence, Union

import pendulum
from more_itertools import take

from instagram_is.feeds import WebApiClient
from instagram_is.models import (
    InstagramUser,
    InstagramPost,
    InstagramPostThumb,
    InstagramComment,
)


# todo: move more functions from stream to here


def sort_n(
    stream: Iterator[Any],
    num: Optional[int],
    key: Optional[Callable] = None,
    reverse: bool = False,
    unique: bool = True,
) -> Sequence[Any]:
    """
    Sort a stream. Processes the whole stream, but loads only num*2 elements in memory.
    :param stream:
    :param num:
    :param key:
    :param reverse:
    :param unique:
    :return:
    """

    results = []
    while True:
        buffer = take(num, stream)
        if not buffer:
            return results
        if unique:
            buffer = set(buffer)
        results.extend(buffer)
        results = sorted(results, key=key, reverse=reverse)[:num]


def _get_datetime(d: Union[int, str, datetime, pendulum.datetime]) -> pendulum.datetime:
    if isinstance(d, str):
        return pendulum.parse(d, tz="UTC")
    if isinstance(d, int):
        return pendulum.from_timestamp(d, tz="UTC")
    if isinstance(d, datetime):
        return pendulum.instance(d, tz="UTC")
    return d


def _to_int(val, default=None) -> Optional[int]:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _to_bool(val, default=None) -> Optional[bool]:
    try:
        return bool(val)
    except (ValueError, TypeError):
        return default


def _timestamp_to_datetime(val, default=None) -> Union[pendulum.datetime, None]:
    try:
        return pendulum.from_timestamp(val)
    except (ValueError, TypeError):
        return default


def _get_caption(data) -> str:
    try:
        return data.edge_media_to_caption.edges[0].node.text or ""
    except IndexError:
        return ""


# https://gist.github.com/mahmoud/237eb20108b5805aed5f
_hashtag_re = re.compile("(?:^|\s)[＃#]{1}(\w+)", re.UNICODE)
_mention_re = re.compile("(?:^|\s)[＠@]{1}([^\s#<>[\]|{}]+)", re.UNICODE)


def _get_matches(text: str, pattern) -> Sequence[str]:
    """
    Returns sorted list of unique lower-cased items that match the regex
    :param text: any text
    :return: sorted list of unique lower-cased items
    """
    # todo: test hashtags ending with surrogate pair emojii (e.g. family, flags)
    try:
        # hashtags are case insensitive
        matches = set(s.lower() for s in pattern.findall(text))
    except TypeError:
        # https://stackoverflow.com/questions/43727583/expected-string-or-bytes-like-object
        matches = set()
    # sorted so that equality matching works when updating???
    return tuple(sorted(matches))


def _get_hashtags(text: str) -> Sequence[str]:
    return _get_matches(text, _hashtag_re)


def _get_mentions(text: str) -> Sequence[str]:
    return _get_matches(text, _mention_re)


class Comments(abc.Iterator):
    # todo
    # input a list of posts
    def __next__(self) -> InstagramComment:
        raise NotImplemented


class Users(abc.Iterator):
    @staticmethod
    def get(
        u: Union[
            int, str, InstagramUser, InstagramPost, InstagramPostThumb, InstagramComment
        ]
    ) -> InstagramUser:
        # Be conservative in what you do, be liberal in what you accept
        if isinstance(u, InstagramUser):
            return u
        if isinstance(u, InstagramPost):
            return WebApiClient.user_info(u.owner_username)
        if isinstance(u, InstagramPostThumb):
            return WebApiClient.user_info(u.owner_num_id)
        if isinstance(u, InstagramComment):
            # todo
            raise NotImplemented
        return WebApiClient.user_info(u)

    def __next__(self) -> InstagramUser:
        # todo
        raise NotImplemented


class Posts(abc.Iterator):
    @staticmethod
    def get(
        p: Union[int, str, InstagramPost, InstagramPostThumb, InstagramComment]
    ) -> InstagramPost:
        # Be conservative in what you do, be liberal in what you accept
        if isinstance(p, InstagramPost):
            return p
        if isinstance(p, InstagramPostThumb):
            return WebApiClient.post_info(p.shortcode)
        if isinstance(p, InstagramComment):
            # todo
            raise NotImplemented
        return WebApiClient.post_info(p)

    def __next__(self) -> InstagramPost:
        # todo
        raise NotImplemented


class FollowedBy(abc.Iterator):
    """
    Who is following this user
    """

    # todo
    def __next__(self) -> None:
        raise NotImplemented


class Following(abc.Iterator):
    """
    Who is this user following
    """

    # todo
    def __next__(self) -> None:
        raise NotImplemented


class Likers(abc.Iterator):
    # todo
    def __next__(self) -> None:
        pass
