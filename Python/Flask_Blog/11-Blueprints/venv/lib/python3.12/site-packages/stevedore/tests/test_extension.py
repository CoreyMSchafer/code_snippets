#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

"""Tests for stevedore.extension"""

import importlib.metadata
import operator
from typing import Any
from unittest import mock
import warnings

from stevedore import exception
from stevedore import extension
from stevedore.tests import utils


ALL_NAMES = ['e1', 't1', 't2']
WORKING_NAMES = ['t1', 't2']


class FauxExtension:
    def __init__(self, *args, **kwds):
        self.args = args
        self.kwds = kwds

    def get_args_and_data(self, data):
        return self.args, self.kwds, data


class BrokenExtension:
    def __init__(self, *args, **kwds):
        raise OSError("Did not create")


class TestCallback(utils.TestCase):
    def test_detect_plugins(self):
        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager('stevedore.test.extension')
        names = sorted(em.names())
        self.assertEqual(names, ALL_NAMES)

    def test_get_by_name(self):
        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager('stevedore.test.extension')
        e = em['t1']
        self.assertEqual(e.name, 't1')

    def test_list_entry_points(self):
        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager('stevedore.test.extension')
        n = em.list_entry_points()
        self.assertEqual(
            {'e1', 'e2', 't1', 't2'}, set(map(operator.attrgetter("name"), n))
        )
        self.assertEqual(4, len(n))

    def test_list_entry_points_names(self):
        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager('stevedore.test.extension')
        names = em.entry_points_names()
        self.assertEqual({'e1', 'e2', 't1', 't2'}, set(names))
        self.assertEqual(4, len(names))

    def test_contains_by_name(self):
        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager('stevedore.test.extension')
        self.assertIn('t1', em, True)

    def test_get_by_name_missing(self):
        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager('stevedore.test.extension')
        try:
            em['t3']
        except KeyError:
            pass
        else:
            assert False, 'Failed to raise KeyError'

    def test_load_multiple_times_entry_points(self):
        # We expect to get the same EntryPoint object because we save them
        # in the cache.
        em1: extension.ExtensionManager[Any]
        em1 = extension.ExtensionManager('stevedore.test.extension')
        eps1 = [ext.entry_point for ext in em1]
        em2: extension.ExtensionManager[Any]
        em2 = extension.ExtensionManager('stevedore.test.extension')
        eps2 = [ext.entry_point for ext in em2]
        self.assertIs(eps1[0], eps2[0])

    def test_load_multiple_times_plugins(self):
        # We expect to get the same plugin object (module or class)
        # because the underlying import machinery will cache the values.
        em1: extension.ExtensionManager[Any]
        em1 = extension.ExtensionManager('stevedore.test.extension')
        plugins1 = [ext.plugin for ext in em1]
        em2: extension.ExtensionManager[Any]
        em2 = extension.ExtensionManager('stevedore.test.extension')
        plugins2 = [ext.plugin for ext in em2]
        self.assertIs(plugins1[0], plugins2[0])

    def test_use_cache(self):
        # If we insert something into the cache of entry points,
        # the manager should not have to call into entrypoints
        # to find the plugins.
        cache = extension.ExtensionManager.ENTRY_POINT_CACHE
        cache['stevedore.test.faux'] = []
        with mock.patch(
            'stevedore._cache.get_group_all',
            side_effect=AssertionError('called get_group_all'),
        ):
            em: extension.ExtensionManager[Any]
            em = extension.ExtensionManager('stevedore.test.faux')
            names = em.names()
        self.assertEqual(names, [])

    def test_iterable(self):
        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager('stevedore.test.extension')
        names = sorted(e.name for e in em)
        self.assertEqual(names, ALL_NAMES)

    def test_invoke_on_load(self):
        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager(
            'stevedore.test.extension',
            invoke_on_load=True,
            invoke_args=('a',),
            invoke_kwds={'b': 'B'},
        )
        self.assertEqual(len(em.extensions), 2)
        for e in em.extensions:
            assert e.obj is not None
            self.assertEqual(e.obj.args, ('a',))
            self.assertEqual(e.obj.kwds, {'b': 'B'})

    def test_map_return_values(self):
        def mapped(ext, /, *args, **kwds):
            return ext.name

        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager(
            'stevedore.test.extension', invoke_on_load=True
        )
        results = em.map(mapped)
        self.assertEqual(sorted(results), WORKING_NAMES)

    def test_map_arguments(self):
        objs = []

        def mapped(ext, /, *args, **kwds):
            objs.append((ext, args, kwds))

        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager(
            'stevedore.test.extension', invoke_on_load=True
        )
        em.map(mapped, 1, 2, a='A', b='B')
        self.assertEqual(len(objs), 2)
        names = sorted([o[0].name for o in objs])
        self.assertEqual(names, WORKING_NAMES)
        for o in objs:
            self.assertEqual(o[1], (1, 2))
            self.assertEqual(o[2], {'a': 'A', 'b': 'B'})

    def test_map_eats_errors(self):
        def mapped(ext, /, *args, **kwds):
            raise RuntimeError('hard coded error')

        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager(
            'stevedore.test.extension', invoke_on_load=True
        )
        results = em.map(mapped, 1, 2, a='A', b='B')
        self.assertEqual(results, [])

    def test_map_propagate_exceptions(self):
        def mapped(ext, /, *args, **kwds):
            raise RuntimeError('hard coded error')

        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager(
            'stevedore.test.extension',
            invoke_on_load=True,
            propagate_map_exceptions=True,
        )

        try:
            em.map(mapped, 1, 2, a='A', b='B')
            assert False
        except RuntimeError:
            pass

    def test_map_errors_when_no_plugins(self):
        expected_str = 'No stevedore.test.extension.none extensions found'

        def mapped(ext, /, *args, **kwds):
            pass

        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager(
            'stevedore.test.extension.none', invoke_on_load=True
        )
        try:
            em.map(mapped, 1, 2, a='A', b='B')
        except exception.NoMatches as err:
            self.assertEqual(expected_str, str(err))

    def test_map_method(self):
        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager(
            'stevedore.test.extension', invoke_on_load=True
        )

        result = em.map_method('get_args_and_data', 42)
        self.assertEqual({r[2] for r in result}, {42})

    def test_items(self):
        em: extension.ExtensionManager[Any]
        em = extension.ExtensionManager('stevedore.test.extension')
        expected_output = {(name, em[name]) for name in ALL_NAMES}
        self.assertEqual(expected_output, set(em.items()))


class TestConflictResolution(utils.TestCase):
    def test_ignore_conflicts(self):
        """Test that ignore_conflicts logs a warning when conflicts exist."""
        extensions = [
            extension.Extension(
                'conflict',
                importlib.metadata.EntryPoint(
                    'conflict', 'module1:Class1', 'test.group'
                ),
                type('TestClass1', (), {}),
                None,
            ),
            extension.Extension(
                'conflict',
                importlib.metadata.EntryPoint(
                    'conflict', 'module2:Class2', 'test.group'
                ),
                type('TestClass2', (), {}),
                None,
            ),
        ]

        with self.assertLogs('stevedore.extension', level='WARNING') as log:
            result = extension.ignore_conflicts(
                'test.group', 'conflict', extensions
            )

        self.assertIs(result, extensions[-1])
        self.assertEqual(len(log.records), 1)
        warning_msg = log.records[0].getMessage()
        self.assertIn("multiple implementations found", warning_msg)
        self.assertIn("'conflict' extension", warning_msg)
        self.assertIn("test.group namespace", warning_msg)

    def test_error_on_conflict(self):
        """Test error_on_conflict raises MultipleMatches exception."""
        extensions = [
            extension.Extension(
                'conflict',
                importlib.metadata.EntryPoint(
                    'conflict', 'module1:Class1', 'test.group'
                ),
                type('TestClass1', (), {}),
                None,
            ),
            extension.Extension(
                'conflict',
                importlib.metadata.EntryPoint(
                    'conflict', 'module2:Class2', 'test.group'
                ),
                type('TestClass2', (), {}),
                None,
            ),
        ]

        with self.assertRaises(exception.MultipleMatches) as cm:
            extension.error_on_conflict('test.group', 'conflict', extensions)

        error_msg = str(cm.exception)
        self.assertIn("multiple implementations found", error_msg)
        self.assertIn("'conflict' command", error_msg)
        self.assertIn("test.group namespace", error_msg)

    def test_custom_conflict_resolver(self):
        """Test using a custom conflict resolver function."""

        def first_resolver(namespace, name, extensions):
            return extensions[0]

        ext1 = extension.Extension(
            'test',
            importlib.metadata.EntryPoint(
                'test', 'module1:Class1', 'test.group'
            ),
            type('TestClass1', (), {}),
            None,
        )
        ext2 = extension.Extension(
            'test',
            importlib.metadata.EntryPoint(
                'test', 'module2:Class2', 'test.group'
            ),
            type('TestClass2', (), {}),
            None,
        )

        em = extension.ExtensionManager.make_test_instance(
            [ext1, ext2], conflict_resolver=first_resolver
        )

        # Should get the first extension when accessing by name
        result = em['test']
        self.assertIs(result, ext1)


class TestDeprecations(utils.TestCase):
    def test_verify_requirements(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            extension.ExtensionManager.make_test_instance(
                [], verify_requirements=True
            )

        self.assertEqual(1, len(w))
        self.assertTrue(issubclass(w[-1].category, DeprecationWarning))
        self.assertIn(
            'The verify_requirements argument is now a no-op',
            str(w[-1].message),
        )


class TestExtensionProperties(utils.TestCase):
    def setUp(self):
        self.ext1 = extension.Extension(
            'name',
            importlib.metadata.EntryPoint(
                'name', 'module.name:attribute.name [extra]', 'group_name'
            ),
            mock.Mock(),
            None,
        )
        self.ext2 = extension.Extension(
            'name',
            importlib.metadata.EntryPoint(
                'name', 'module:attribute', 'group_name'
            ),
            mock.Mock(),
            None,
        )

    def test_module_name(self):
        self.assertEqual('module.name', self.ext1.module_name)
        self.assertEqual('module', self.ext2.module_name)

    def test_attr(self):
        self.assertEqual('attribute.name', self.ext1.attr)
        self.assertEqual('attribute', self.ext2.attr)

    def test_entry_point_target(self):
        self.assertEqual(
            'module.name:attribute.name [extra]', self.ext1.entry_point_target
        )
        self.assertEqual('module:attribute', self.ext2.entry_point_target)
