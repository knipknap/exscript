"""pytest configuration for the unittest-based suite."""

import inspect
import unittest


def pytest_pycollect_makeitem(collector, name, obj):
    """Collects TestCase classes only in the module that defines them.

    Several test modules import a base TestCase (e.g. ProtocolTest) to derive
    from it; without this hook pytest would run the base tests once more for
    every importing module.
    """
    if (
        inspect.isclass(obj)
        and issubclass(obj, unittest.TestCase)
        and obj.__module__ != collector.module.__name__
    ):
        return []
    return None
