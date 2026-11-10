#
# Copyright (C) 2010-2017 Samuel Abels
# The MIT License (MIT)
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
The collection of the work queue: a queue of items that also tracks the
items in progress.
"""

from collections import deque
from collections.abc import Callable, Hashable
from threading import Condition, RLock
from typing import Any, cast
from uuid import uuid4


class Pipeline:
    """
    A collection that is similar to Python's Queue object, except
    it also tracks items that are currently sleeping or in progress.
    """

    def __init__(self, max_working: int = 1) -> None:
        """
        Constructor.

        :param max_working: The maximum number of items in progress.
        """
        self.condition = Condition(RLock())
        self.max_working = max_working
        self.running = True
        self.paused = False
        # clear() sets the containers; the casts are for the type checker.
        # Any: the items are any hashable objects (the work queue adds Job
        # objects), and the pipeline returns them as they are. name2id never
        # has the key None, but get_from_name() looks it up.
        self.queue: deque[Any] = cast('deque[Any]', None)
        self.force: deque[Any] = cast('deque[Any]', None)
        self.sleeping: set[Any] = cast('set[Any]', None)
        self.working: set[Any] = cast('set[Any]', None)
        self.item2id: dict[Any, str] = cast('dict[Any, str]', None)
        self.id2item: dict[str, Any] = cast('dict[str, Any]', None)  # for performance reasons
        self.name2id: dict[str | None, str] = cast('dict[str | None, str]', None)
        self.id2name: dict[str, str] = cast('dict[str, str]', None)
        self.clear()

    def __len__(self) -> int:
        with self.condition:
            return len(self.id2item)

    def __contains__(self, item: object) -> bool:
        with self.condition:
            return item in self.item2id

    def _register_item(self, name: str | None, item: Hashable) -> str:
        """
        Registers the given item under a new id, and under the given name
        unless it is None. Raises an AttributeError, and registers nothing,
        if an item with the name is registered already.

        :return: The id of the item.
        """
        if name in self.name2id:
            msg = 'an item named %s is already queued' % repr(name)
            raise AttributeError(msg)
        uuid = uuid4().hex
        self.id2item[uuid] = item
        self.item2id[item] = uuid
        if name is None:
            return uuid
        self.name2id[name] = uuid
        self.id2name[uuid] = name
        return uuid

    def get_from_name(self, name: str | None) -> Any:
        """
        Returns the item with the given name, or None if no such item
        is known.
        """
        with self.condition:
            try:
                item_id = self.name2id[name]
            except KeyError:
                return None
            return self.id2item[item_id]
        return None

    def has_id(self, item_id: str) -> bool:
        """
        Returns True if the queue contains an item with the given id.
        """
        return item_id in self.id2item

    def task_done(self, item: Hashable) -> None:
        """
        Removes the given item, which was in progress, from the pipeline,
        and wakes up the threads that wait on the pipeline.
        """
        with self.condition:
            try:
                self.working.remove(item)
            except KeyError:
                # This may happen if we receive a notification from a
                # thread that was previously enqueued, but then the
                # workqueue was forcefully stopped without waiting for
                # child threads to complete.
                self.condition.notify_all()
                return
            item_id = self.item2id.pop(item)
            self.id2item.pop(item_id)
            try:
                name = self.id2name.pop(item_id)
            except KeyError:
                pass
            else:
                self.name2id.pop(name)
            self.condition.notify_all()

    def append(self, item: Hashable, name: str | None = None) -> str:
        """
        Adds the given item to the end of the pipeline.

        :param name: A unique name for the item, see get_from_name().
        :raises AttributeError: If an item with the name is queued already;
            the pipeline is unchanged then.
        :return: The id of the item.
        """
        with self.condition:
            uuid = self._register_item(name, item)
            self.queue.append(item)
            self.condition.notify_all()
            return uuid

    def appendleft(self, item: Hashable, name: str | None = None, force: bool = False) -> str:
        """
        Adds the given item to the start of the pipeline. A forced item is
        returned by next() before all others, even if max_working items are
        in progress already.

        :param name: A unique name for the item, see get_from_name().
        :param force: Whether the item is forced.
        :raises AttributeError: If an item with the name is queued already;
            the pipeline is unchanged then.
        :return: The id of the item.
        """
        with self.condition:
            uuid = self._register_item(name, item)
            if force:
                self.force.append(item)
            else:
                self.queue.appendleft(item)
            self.condition.notify_all()
            return uuid

    def prioritize(self, item: Hashable, force: bool = False) -> None:
        """
        Moves the item to the very left of the queue. Does nothing if the
        item is in progress or forced already.

        :param force: Whether to force the item, see appendleft().
        """
        with self.condition:
            # If the job is already running (or about to be forced),
            # there is nothing to be done.
            if item in self.working or item in self.force:
                return
            self.queue.remove(item)
            if force:
                self.force.append(item)
            else:
                self.queue.appendleft(item)
            self.condition.notify_all()

    def clear(self) -> None:
        """
        Removes all items, and wakes up the threads that wait on the pipeline.
        """
        with self.condition:
            self.queue = deque()
            self.force = deque()
            self.sleeping = set()
            self.working = set()
            self.item2id = dict()
            self.id2item = dict()
            self.name2id = dict()
            self.id2name = dict()
            self.condition.notify_all()

    def stop(self) -> None:
        """
        Force the next() method to return while in another thread.
        The return value of next() will be None.
        """
        with self.condition:
            self.running = False
            self.condition.notify_all()

    def start(self) -> None:
        """
        Undoes stop(): next() returns items again.
        """
        with self.condition:
            self.running = True
            self.condition.notify_all()

    def pause(self) -> None:
        """
        Makes next() wait until unpause() is called.
        """
        with self.condition:
            self.paused = True
            self.condition.notify_all()

    def unpause(self) -> None:
        """
        Undoes pause(): next() returns items again.
        """
        with self.condition:
            self.paused = False
            self.condition.notify_all()

    def sleep(self, item: Hashable) -> None:
        """
        Marks the given item as sleeping until wake() is called: next()
        skips it, and it does not count against max_working.
        """
        with self.condition:
            self.sleeping.add(item)
            self.condition.notify_all()

    def wake(self, item: Hashable) -> None:
        """
        Undoes sleep() for the given item, which must be sleeping.
        """
        assert item in self.sleeping
        with self.condition:
            self.sleeping.remove(item)
            self.condition.notify_all()

    def wait_for_id(self, item_id: str) -> None:
        """
        Waits until the item with the given id is removed from the pipeline.
        """
        with self.condition:
            while self.has_id(item_id):
                self.condition.wait()

    def wait(self) -> None:
        """
        Waits for all currently running tasks to complete.
        """
        with self.condition:
            while self.working:
                self.condition.wait()

    def wait_all(self) -> None:
        """
        Waits for all queued and running tasks to complete.
        """
        with self.condition:
            while len(self) > 0:
                self.condition.wait()

    def with_lock[R](self, function: Callable[..., R], *args: Any, **kwargs: Any) -> R:
        """
        Calls the given function with the pipeline and the given arguments
        while holding the lock of the pipeline.

        :return: The result of the function.
        """
        with self.condition:
            return function(self, *args, **kwargs)

    def set_max_working(self, max_working: int) -> None:
        """
        Sets the maximum number of items in progress.
        """
        with self.condition:
            self.max_working = int(max_working)
            self.condition.notify_all()

    def get_max_working(self) -> int:
        """
        Returns the maximum number of items in progress.
        """
        return self.max_working

    def get_working(self) -> list[Any]:
        """
        Returns a list of the items in progress.
        """
        return list(self.working)

    def _popleft_sleeping(self) -> list[Any]:
        """
        Removes the sleeping items from the start of the queue, and returns
        them.
        """
        sleeping: list[Any] = []
        while True:
            try:
                node = self.queue[0]
            except IndexError:
                break
            if node not in self.sleeping:
                break
            sleeping.append(node)
            self.queue.popleft()
        return sleeping

    def _get_next(self, pop: bool = True) -> Any:
        """
        Returns the first item of the queue that is not sleeping, or None.

        :param pop: Whether to remove the item from the queue.
        """
        # We need to leave sleeping items in the queue because else we
        # would not know their original position after they wake up.
        # So we need to temporarily remove sleeping items from the top of
        # the queue here.
        sleeping = self._popleft_sleeping()

        # Get the first non-sleeping item from the queue.
        if pop:
            try:
                next = self.queue.popleft()
            except IndexError:
                next = None
        else:
            try:
                next = self.queue[0]
            except IndexError:
                next = None

        # Re-insert sleeping items, in their order.
        self.queue.extendleft(reversed(sleeping))
        return next

    def try_next(self) -> Any:
        """
        Like next(), but only returns the item that would be selected
        right now, without waiting and without changing the queue.
        """
        with self.condition:
            try:
                return self.force[0]
            except IndexError:
                pass

            return self._get_next(False)

    def __next__(self) -> Any:
        with self.condition:
            while self.running:
                if self.paused:
                    self.condition.wait()
                    continue

                # Wait until enough slots are available.
                if len(self.working) - len(self.sleeping) - len(self.force) >= self.max_working:
                    self.condition.wait()
                    continue

                # Forced items are returned regardless of how many tasks
                # are already working.
                try:
                    next = self.force.popleft()
                except IndexError:
                    pass
                else:
                    self.working.add(next)
                    return next

                # Return the first non-sleeping task.
                next = self._get_next()
                if next is None:
                    self.condition.wait()
                    continue
                self.working.add(next)
                return next
        return None
