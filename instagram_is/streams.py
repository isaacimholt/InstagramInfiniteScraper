from __future__ import annotations

import csv
from collections import abc
from datetime import datetime
from functools import partial
from itertools import dropwhile, islice, chain
from operator import attrgetter
from typing import (
    Callable,
    Iterator,
    Any,
    Optional,
    Sequence,
    Union,
    TypeVar,
    NamedTuple,
)

import pendulum
from more_itertools import unique_everseen

from instagram_is.tools import sort_n, _get_datetime
from .models import InstagramPostThumb, InstagramPost, InstagramUser, InstagramComment

ANY_MODEL = Union[InstagramPostThumb, InstagramPost, InstagramUser, InstagramComment]


class StreamMuxer(abc.Iterator):
    """
    Proxy object that handles applying changes to individual streams.
    Once iteration has begun, these smaller feeds are combined to act as a single stream.
    """

    def __init__(self, streams):
        self._streams = streams

    def __next__(self) -> ANY_MODEL:
        return next(self.__iter__())

    def __iter__(self) -> Iterator[ANY_MODEL]:
        # try hard not to use round robin -- roundrobin and interleave_longest accept
        # only *args, not an iterable of iterables, which means possibly a large
        # quantity of streams will be initialized in memory from the muxer, and each
        # with the first batch of results loaded in memory. Even if it was not the case
        # that it accepted only *args, using a roundrobin would still load each stream's
        # first batch of results.
        return chain.from_iterable(self._streams)

    def map_streams(self, fxn: Callable) -> None:
        self._streams = map(fxn, self._streams)


T = TypeVar("T")


class GenericStream(Iterator[T]):
    def __next__(self) -> T:
        return next(self)

    def merge_streams(self):
        # must be of same iterable type
        raise NotImplementedError

    def property_stream(self, prop: str):
        return (getattr(i, prop) for i in self)

    def run(self) -> None:
        for _ in self:
            # allow stream to perform stored actions
            pass

    def map(self, fxn: Callable):
        raise NotImplementedError
        return GenericStream(map(fxn, self))


class NamedTupleStream(GenericStream[NamedTuple]):
    def __init__(self, *feeds: Iterator[NamedTuple], log_progress=100):

        # why _stream & _stream_muxer?
        # some operations work on individual streams, instead of the chained version
        # these operations must be allowed to be applied at any time before iteration
        self._stream_muxer = StreamMuxer(feeds)
        self._stream = self._stream_muxer

        self.log_progress = log_progress

    def __iter__(self) -> Iterator[NamedTuple]:
        # todo: move into generic stream
        for i, e in enumerate(self._stream, 1):
            if self.log_progress and i % self.log_progress == 0:
                print(f"Streamed {i} elements.")
            yield e

    def limit(self, max_results: int) -> NamedTupleStream:
        # todo: move into generic stream
        self._stream = islice(self._stream, max_results)
        return self

    def unique(self) -> NamedTupleStream:
        """
        Caution: Loads all elements into memory to determine uniqueness.
        """
        self._stream = unique_everseen(self._stream)
        return self

    def sort(
        self, key: Optional[Callable] = None, reverse: bool = True
    ) -> NamedTupleStream:
        """
        Caution: Loads all elements into memory to perform sorting.
        """
        self._stream = (i for i in sorted(self._stream, key=key, reverse=reverse))
        return self

    def top(self, num: int, attr: str, unique: bool = True) -> NamedTupleStream:
        self._stream = sort_n(
            self._stream, num=num, key=attrgetter(attr), reverse=True, unique=unique
        )
        # todo: move into generic stream
        return self

    def filter(
        self, predicate: Callable, max_tail_skip: Optional[int] = None
    ) -> NamedTupleStream:
        # todo: move into generic stream
        filter_partial = partial(
            self._filter, predicate=predicate, max_tail_skip=max_tail_skip
        )
        self._stream_muxer.map_streams(filter_partial)

        return self

    def filter_range(
        self,
        attr: str,
        gte: Optional[Any] = None,
        lte: Optional[Any] = None,
        max_tail_skip: Optional[int] = None,
    ):
        # todo: possibly delete
        def filter_predicate(e: Any) -> bool:
            if gte is not None and getattr(e, attr) < gte:
                return False
            if lte is not None and getattr(e, attr) > lte:
                return False
            return True

        return self.filter(predicate=filter_predicate, max_tail_skip=max_tail_skip)

    def created_range(
        self,
        after: Union[int, str, datetime, pendulum.datetime],
        before: Union[int, str, datetime, pendulum.datetime],
        attr: str = "created_at",
        max_tail_skip: Optional[int] = 50,
    ) -> NamedTupleStream:
        """
        Filter posts *created* in specified date range.
        Note that this may be different than instagram feed since older posts that were
        recently *modified* will not appear in this stream.

        :param after: created; further back in time (smaller datetime)
        :param before: created; more recent (larger datetime)
        :param attr:
        :param max_tail_skip:
        :return:
        """

        return self.filter_range(
            attr=attr,
            gte=_get_datetime(after),
            lte=_get_datetime(before),
            max_tail_skip=max_tail_skip,
        )

    @staticmethod
    def _filter(
        stream: Iterator[Any], predicate: Callable, max_tail_skip: Optional[int] = 50
    ):
        """
        Ignore items from stream until predicate is true, then yield items until predicate
        is false, at which point the stream is exited.
        :param stream: stream of items to filter
        :param predicate:
        :return: elements of the stream
        """
        # todo: move into generic stream

        if not max_tail_skip:
            yield from filter(predicate, stream)

        stream = dropwhile(lambda x: not predicate(x), stream)

        # elements we need start now
        skipped = 0
        for e in stream:
            if predicate(e):
                yield e
                skipped = 0
            elif skipped >= max_tail_skip:
                return
            else:
                skipped += 1

    def save_csv(
        self, file_name: str, header_row: Optional[Sequence[str]] = None
    ) -> NamedTupleStream:
        # todo: move into generic stream
        with open(file_name, "w", newline="", encoding="utf-8") as csv_file:
            # using newline='' corrects empty lines
            writer = csv.writer(csv_file)

            for i in self:
                if not header_row:
                    header_row = i._fields
                    writer.writerow(header_row)
                writer.writerow(i)
                yield i


class ThumbStream(NamedTupleStream[InstagramPostThumb]):
    def post_stream(self):
        raise NotImplementedError

    def owner_stream(self):
        raise NotImplementedError

    def hashtag_streams(self):
        # list of streams
        raise NotImplementedError


class PostStream(NamedTupleStream[InstagramPost]):
    def thumb_stream(self):
        raise NotImplementedError

    def owner_stream(self):
        raise NotImplementedError

    def location_stream(self):
        raise NotImplementedError

    def comment_stream(self):
        raise NotImplementedError

    def photo_user_stream(self):
        """
        Return stream of users present in photo, if any.
        """
        raise NotImplementedError

    def hashtag_streams(self):
        # list of streams
        raise NotImplementedError


class UserStream(NamedTupleStream[InstagramUser]):
    def post_stream(self):
        raise NotImplementedError


class CommentStream(NamedTupleStream[InstagramComment]):
    def owner_stream(self):
        raise NotImplementedError

    def commenter_stream(self):
        raise NotImplementedError
