"""
Collection types.
"""

import copy
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, Self, cast


class OrderedDefaultDict[K, V](OrderedDict[K, V]):
    """
    A fusion of Python's defaultdict and Python's OrderedDict.
    """

    def __init__(self, default_factory: Callable[[], V] | None = None, *a: Any, **kw: Any) -> None:
        """
        Constructor. The other arguments are passed to OrderedDict.

        :param default_factory: Called without arguments to create the value
            of a missing key; if it is None, a missing key raises KeyError.
        """
        # mypy rejects the Callable ABC in isinstance().
        if default_factory is not None and not isinstance(default_factory, cast(Any, Callable)):
            raise TypeError('first argument must be callable')
        OrderedDict.__init__(self, *a, **kw)
        self.default_factory: Callable[[], V] | None = default_factory

    def __getitem__(self, key: K) -> V:
        try:
            return OrderedDict.__getitem__(self, key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key: K) -> V:
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self) -> tuple[Any, ...]:
        if self.default_factory is None:
            args: tuple[Callable[[], V], ...] = tuple()
        else:
            args = (self.default_factory,)
        return type(self), args, None, None, iter(self.items())

    def copy(self) -> Self:
        """
        Returns a shallow copy, with the same default factory.
        """
        return self.__copy__()

    def __copy__(self) -> Self:
        return type(self)(self.default_factory, self)

    def __deepcopy__(self, memo: dict[int, Any]) -> Self:
        result = type(self)(self.default_factory)
        memo[id(self)] = result  # for values that refer to this dictionary
        for key, value in self.items():
            result[copy.deepcopy(key, memo)] = copy.deepcopy(value, memo)
        return result

    def __repr__(self) -> str:
        return 'OrderedDefaultDict(%s, %s)' % (self.default_factory, OrderedDict.__repr__(self))
