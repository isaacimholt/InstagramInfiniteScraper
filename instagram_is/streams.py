from __future__ import annotations

import heapq
import logging
from collections.abc import Iterator as ABCIterator
from itertools import takewhile, dropwhile, islice
from operator import attrgetter
from typing import Callable, Iterator, Union, Any, List, Optional

import pendulum

from .models import InstagramPostThumb, InstagramPost, InstagramUser


class BaseStream(ABCIterator):
    def __init__(self, stream, log_progress=1000):
        self.stream = stream
        self.log_progress = log_progress

    def __iter__(self):
        for i, e in enumerate(self.stream, 1):
            if self.log_progress and i % self.log_progress == 0:
                print(f"Streamed {i} elements.")
            yield e

    def limit(self, max_results: int) -> BaseStream:
        self.stream = islice(self.stream, max_results)
        return self

    def to_list(self, sort: Optional[str] = None) -> List:
        mylist = list(self.stream)
        if sort:
            mylist.sort(key=attrgetter(sort), reverse=True)
        return mylist

    def filter_date_created(self,
                            start: pendulum.datetime,
                            end: pendulum.datetime,
                            buffer_size: int = 100) -> BaseStream:
        """

        :param start: further back in time (smaller datetime)
        :param end: more recent (larger datetime)
        :param buffer_size: results are buffered to sort them first
        :return:
        """

        def filter_predicate(p: InstagramPostThumb) -> bool:
            if start and p.created_at < start:
                return False
            if end and p.created_at > end:
                return False
            return True

        def order_key(p: InstagramPostThumb) -> int:
            return now.int_timestamp - p.created_at.int_timestamp

        now = pendulum.now('UTC')

        # preemptively filter near the date ranges given
        # must leave some "wrong" results on either end for _partition_filter to trigger stream exit
        self.stream = filter(
            lambda x: end.add(days=1) > x.created_at > start.subtract(days=1),
            self.stream)
        # must sort first otherwise wrong results
        self.stream = self._buffered_sort(self.stream, order_key, buffer_size)
        # stop iterating after receiving item outside of date range
        self.stream = self._partition_filter(self.stream, filter_predicate)

        return self

    @staticmethod
    def _buffered_sort(stream: Iterator[Any],
                       key: Union[Callable, None] = None,
                       buffer: int = 100):
        """
        Make best-effort attempt to order (asc) results from a stream.
        info on key: https://docs.python.org/3/glossary.html#term-key-function
        :param key: function applied to elements to decide order, smallest -> largest
        :param stream: stream of items to order
        :param buffer: sorted buffer to push/pop from
        :return: elements of the stream
        """

        def _get(item):
            if key is not None:
                return item[1]
            else:
                return item

        heap = []
        prev = None  # keep track of last element to warn in case elements are not sorted
        for i in stream:
            if key is not None:
                i = (key(i), i)
            if buffer:
                heapq.heappush(heap, i)
                buffer -= 1
                continue
            curr = heapq.heappushpop(heap, i)
            if prev is not None and curr < prev:
                logging.warning(
                    "Stream order is compromised, if order is important increase buffer size")
            yield _get(curr)
            prev = curr
        while heap:
            yield _get(heapq.heappop(heap))

    @staticmethod
    def _partition_filter(stream: Iterator[Any], predicate: Callable):
        """
        Ignore items from stream until predicate is true, then yield items until predicate is
        false, at which point the stream is exited.
        :param stream: stream of items to filter
        :param predicate:
        :return: elements of the stream
        """
        stream = dropwhile(lambda x: not predicate(x), stream)
        stream = takewhile(predicate, stream)
        yield from stream


class ThumbStream(BaseStream):
    def __next__(self) -> InstagramPostThumb:
        return next(super())


class PostStream(BaseStream):
    def __next__(self) -> InstagramPost:
        return next(super())


class UserStream(BaseStream):
    def __next__(self) -> InstagramUser:
        return next(super())
