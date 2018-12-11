from __future__ import annotations

import csv
import heapq
import logging
from collections.abc import Iterator as ABCIterator
from itertools import dropwhile, islice
from operator import attrgetter
from typing import Callable, Iterator, Any, List, Optional, Sequence

import pendulum
from more_itertools import roundrobin

from .models import InstagramPostThumb, InstagramPost, InstagramUser


class BaseStream(ABCIterator):
    def __init__(self, *streams, log_progress=1000):
        self._streams = list(streams)
        self.stream = None
        self.log_progress = log_progress

    def __iter__(self):
        for i, e in enumerate(self.stream, 1):
            if self.log_progress and i % self.log_progress == 0:
                print(f"Streamed {i} elements.")
            yield e

    def _get_stream(self):
        return self.stream or roundrobin(*self._streams)

    def limit(self, max_results: int) -> BaseStream:
        # must combine streams to apply limit
        self.stream = islice(self._get_stream(), max_results)
        return self

    def to_list(self, sort: Optional[str] = None) -> List:
        mylist = list(self._get_stream())
        if sort:
            mylist.sort(key=attrgetter(sort), reverse=True)
        return mylist

    def date_range(self,
                   start: pendulum.datetime,
                   end: pendulum.datetime) -> BaseStream:
        """
        Filter posts *created* in specified date range.
        Note that this may be different than instagram feed since older posts that were
        recently *modified* will not appear in this stream.

        :param start: created; further back in time (smaller datetime)
        :param end: created; more recent (larger datetime)
        :return:
        """

        if self.stream:
            logging.warning(f"Apply date_range after other operators but before to_* "
                            f"methods.")

        now = pendulum.now('UTC')

        def filter_predicate(p: InstagramPostThumb) -> bool:
            if start and p.created_at < start:
                return False
            if end and p.created_at > end:
                return False
            return True

        def order_key(p: InstagramPostThumb) -> int:
            return now.int_timestamp - p.created_at.int_timestamp

        # stop iterating after receiving item outside of date range
        self._streams[:] = [self._strip(s, filter_predicate) for s in self._streams]
        # self.stream = self._strip(self.stream, filter_predicate, 2*buffer_size*self.stream_count)
        # must sort first otherwise wrong results
        # self.stream = self._buffered_sort(self.stream, order_key, buffer_size)

        return self

    @staticmethod
    def _buffered_sort(stream: Iterator[Any],
                       key: Optional[Callable] = None,
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
    def _strip(stream: Iterator[Any], predicate: Callable, stop_after: int = 50):
        """
        Ignore items from stream until predicate is true, then yield items until predicate is
        false, at which point the stream is exited.
        :param stream: stream of items to filter
        :param predicate:
        :return: elements of the stream
        """

        stream = dropwhile(lambda x: not predicate(x), stream)

        # elements we need start now
        dropped = 0
        for e in stream:
            if predicate(e):
                yield e
                dropped = 0
            elif dropped >= stop_after:
                print("torna n'ata vota, jesù crì")
                return
            else:
                dropped += 1

    @staticmethod
    def _save_csv(stream: Iterator, file_name: str, header_row: Sequence[str]) -> None:
        with open(file_name, 'w', newline='', encoding='utf-8') as csv_file:
            # using newline='' corrects empty lines
            writer = csv.writer(csv_file)
            writer.writerow(header_row)
            writer.writerows(stream)


class ThumbStream(BaseStream):
    def __next__(self) -> InstagramPostThumb:
        return next(super())

    def to_csv(self,
               file_name: str,
               header_row: Sequence[str] = InstagramPostThumb._fields) -> None:
        return self._save_csv(self._get_stream(), file_name, header_row)


class PostStream(BaseStream):
    def __next__(self) -> InstagramPost:
        return next(super())

    def to_csv(self,
               file_name: str,
               header_row: Sequence[str] = InstagramPost._fields) -> None:
        return self._save_csv(self._get_stream(), file_name, header_row)


class UserStream(BaseStream):
    def __next__(self) -> InstagramUser:
        return next(super())

    def to_csv(self,
               file_name: str,
               header_row: Sequence[str] = InstagramUser._fields) -> None:
        return self._save_csv(self._get_stream(), file_name, header_row)
