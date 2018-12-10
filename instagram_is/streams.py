import heapq
import logging
from collections.abc import Iterator as ABCIterator
from datetime import datetime
from itertools import takewhile, dropwhile, islice
from typing import Callable, Iterator, Union, Any

import pendulum

from .models import InstagramPostThumb, InstagramPost, InstagramUser


class BaseStream(ABCIterator):
    def __init__(self, stream):
        self.stream = stream
        self.sorted = False

    def limit(self, max_results: int):
        self.stream = islice(self.stream, max_results)
        return self

    def created_range(self, begin: datetime, end: datetime, buffer_size: int = 100):

        def filter_predicate(p: InstagramPostThumb) -> bool:
            if begin and p.created_at < begin:
                return False
            if end and p.created_at > end:
                return False
            return True

        def order_key(p: InstagramPostThumb) -> int:
            return now.int_timestamp - p.created_at.int_timestamp

        now = pendulum.now('UTC')

        # must sort first otherwise wrong results
        self.stream = self._buffered_sort(self.stream, order_key, buffer_size)
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
        return next(self.stream)


class PostStream(BaseStream):
    def __next__(self) -> InstagramPost:
        return next(self.stream)


class UserStream(BaseStream):
    def __next__(self) -> InstagramUser:
        return next(self.stream)
