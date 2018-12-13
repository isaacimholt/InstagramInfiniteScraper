from __future__ import annotations

import csv
from abc import ABC
from collections import abc
from datetime import datetime
from functools import partial
from itertools import dropwhile, islice, chain
from operator import attrgetter
from typing import Callable, Iterator, Any, List, Optional, Sequence, Set, Union

import pendulum
from more_itertools import unique_everseen

from instagram_is.tools import sort_n, _get_datetime
from .models import InstagramPostThumb, InstagramPost, InstagramUser, InstagramComment

ANY_MODEL = Union[InstagramPostThumb, InstagramPost, InstagramUser]


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
        return chain.from_iterable(self._streams)

    def map_streams(self, fxn: Callable) -> None:
        self._streams = map(fxn, self._streams)


class BaseStream(abc.Iterator, ABC):
    def __init__(self, *feeds: Iterator[ANY_MODEL], log_progress=100):

        # why _stream & _stream_muxer?
        # some operations work on individual streams, instead of the chained version
        # these operations must be allowed to be applied at any time before iteration
        self._stream_muxer = StreamMuxer(feeds)
        self._stream = self._stream_muxer

        self.log_progress = log_progress

    def __iter__(self) -> Iterator[ANY_MODEL]:
        for i, e in enumerate(self._stream, 1):
            if self.log_progress and i % self.log_progress == 0:
                print(f"Streamed {i} elements.")
            yield e

    def limit(self, max_results: int) -> BaseStream:
        # must combine streams to apply limit
        self._stream = islice(self._stream, max_results)
        return self

    def unique(self) -> BaseStream:
        """
        Must keep elements in memory to determine uniqueness
        :return:
        """
        self._stream = unique_everseen(self._stream)
        return self

    def to_list(self, sort: Optional[str] = None, reverse=True) -> List:
        if sort:
            return sorted(self._stream, key=attrgetter(sort), reverse=reverse)
        return list(self._stream)

    def to_set(self) -> Set:
        return set(self._stream)

    def top(self, num: int, attr: str, unique: bool = True) -> BaseStream:
        self._stream = sort_n(
            self._stream, num=num, key=attrgetter(attr), reverse=True, unique=unique
        )
        return self

    def filter(
        self, predicate: Callable, max_tail_skip: Optional[int] = None
    ) -> BaseStream:

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
        def filter_predicate(e: Any) -> bool:
            if gte is not None and getattr(e, attr) < gte:
                return False
            if lte is not None and getattr(e, attr) > lte:
                return False
            return True

        return self.filter(predicate=filter_predicate, max_tail_skip=max_tail_skip)

    def date_range(
        self,
        after: Union[int, str, datetime, pendulum.datetime],
        before: Union[int, str, datetime, pendulum.datetime],
        attr: str = "created_at",
        max_tail_skip: Optional[int] = 50,
    ) -> BaseStream:
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

    @staticmethod
    def _save_csv(stream: Iterator, file_name: str, header_row: Sequence[str]) -> None:
        with open(file_name, "w", newline="", encoding="utf-8") as csv_file:
            # using newline='' corrects empty lines
            writer = csv.writer(csv_file)
            writer.writerow(header_row)
            writer.writerows(stream)


class ThumbStream(BaseStream):
    def __next__(self) -> InstagramPostThumb:
        return next(super())

    def to_csv(
        self, file_name: str, header_row: Sequence[str] = InstagramPostThumb._fields
    ) -> None:
        return self._save_csv(self._stream, file_name, header_row)


class PostStream(BaseStream):
    def __next__(self) -> InstagramPost:
        return next(super())

    def to_csv(
        self, file_name: str, header_row: Sequence[str] = InstagramPost._fields
    ) -> None:
        return self._save_csv(self._stream, file_name, header_row)


class UserStream(BaseStream):
    def __next__(self) -> InstagramUser:
        return next(super())

    def to_csv(
        self, file_name: str, header_row: Sequence[str] = InstagramUser._fields
    ) -> None:
        return self._save_csv(self._stream, file_name, header_row)


class CommentStream(BaseStream):
    def __next__(self) -> InstagramComment:
        return next(super())

    def to_csv(
            self, file_name: str, header_row: Sequence[str] = InstagramComment._fields
    ) -> None:
        return self._save_csv(self._stream, file_name, header_row)
