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

"""ExtensionManager"""

from collections.abc import Callable
from collections.abc import ItemsView
from collections.abc import Iterator
import importlib.metadata
import itertools
import logging
import operator
from typing import Any
from typing import Concatenate
from typing import Generic
from typing import ParamSpec
from typing import TYPE_CHECKING
from typing import TypeAlias
from typing import TypeVar
import warnings

from . import _cache
from .exception import MultipleMatches
from .exception import NoMatches

if TYPE_CHECKING:
    from typing_extensions import Self

LOG = logging.getLogger(__name__)

T = TypeVar('T')
U = TypeVar('U')
P = ParamSpec('P')


class Extension(Generic[T]):
    """Book-keeping object for tracking extensions.

    The arguments passed to the constructor are saved as attributes of
    the instance using the same names, and can be accessed by the
    callables passed to :meth:`map` or when iterating over an
    :class:`ExtensionManager` directly.

    :param name: The entry point name.
    :param entry_point: The EntryPoint instance returned by :mod:`entrypoints`.
    :param plugin: The value returned by entry_point.load()
    :param obj: The object returned by ``plugin(*args, **kwds)`` if the
                manager invoked the extension on load.

    """

    def __init__(
        self,
        name: str,
        entry_point: importlib.metadata.EntryPoint,
        plugin: Callable[..., T],
        obj: T | None,
    ) -> None:
        self.name = name
        self.entry_point = entry_point
        self.plugin = plugin
        self.obj = obj

    @property
    def module_name(self) -> str:
        """The name of the module from which the entry point is loaded.

        :return: A string in 'dotted.module' format.
        """
        return self.entry_point.module

    @property
    def attr(self) -> str:
        """The attribute of the module to be loaded."""
        return self.entry_point.attr

    @property
    def entry_point_target(self) -> str:
        """The module and attribute referenced by this extension's entry_point.

        :return: A string representation of the target of the entry point in
            'dotted.module:object' format.
        """
        return self.entry_point.value


#: OnLoadFailureCallbackT defines the type for callbacks when a plugin fails
#: to load. The callback callable should expect the extension manager instance,
#: the underlying entrypoint instance, and the exception raised during
#: attempted loading.
OnLoadFailureCallbackT: TypeAlias = Callable[
    ['ExtensionManager[T]', importlib.metadata.EntryPoint, BaseException], None
]

#: ConflictResolver defines the type for conflict resolution callables. The
#: callable should expect the extension namespace, extension name, and a list
#: of the entrypoints themselves.
ConflictResolverT: TypeAlias = Callable[
    [str, str, list[Extension[T]]], Extension[T]
]


def ignore_conflicts(
    namespace: str, name: str, entrypoints: list[Extension[T]]
) -> Extension[T]:
    LOG.warning(
        "multiple implementations found for the '%(name)s' extension in "
        "%(namespace)s namespace: %(conflicts)s",
        {
            'name': name,
            'namespace': namespace,
            'conflicts': ', '.join(
                ep.plugin.__qualname__ for ep in entrypoints
            ),
        },
    )
    # use the most last found entrypoint
    return entrypoints[-1]


def error_on_conflict(
    namespace: str, name: str, entrypoints: list[Extension[T]]
) -> Extension[T]:
    raise MultipleMatches(
        "multiple implementations found for the '{name}' command in "
        "{namespace} namespace: {conflicts}".format(
            name=name,
            namespace=namespace,
            conflicts=', '.join(ep.plugin.__qualname__ for ep in entrypoints),
        )
    )


class ExtensionManager(Generic[T]):
    """Base class for all of the other managers.

    :param namespace: The namespace for the entry points.
    :param invoke_on_load: Boolean controlling whether to invoke the
        object returned by the entry point after the driver is loaded.
    :param invoke_args: Positional arguments to pass when invoking
        the object returned by the entry point. Only used if invoke_on_load
        is True.
    :param invoke_kwds: Named arguments to pass when invoking
        the object returned by the entry point. Only used if invoke_on_load
        is True.
    :param propagate_map_exceptions: Boolean controlling whether exceptions
        are propagated up through the map call or whether they are logged and
        then ignored
    :param on_load_failure_callback: Callback function that will be called when
        an entrypoint can not be loaded. The arguments that will be provided
        when this is called (when an entrypoint fails to load) are
        (manager, entrypoint, exception)
    :param verify_requirements: **DEPRECATED** This is a no-op and will be
        removed in a future version.
    :param conflict_resolver: A callable that determines what to do in the
        event that there are multiple entrypoints in the same group with the
        same name. This is only used if retrieving entrypoint by name.
    """

    ENTRY_POINT_CACHE: dict[str, list[importlib.metadata.EntryPoint]] = {}

    def __init__(
        self,
        namespace: str,
        invoke_on_load: bool = False,
        invoke_args: tuple[Any, ...] | None = None,
        invoke_kwds: dict[str, Any] | None = None,
        propagate_map_exceptions: bool = False,
        on_load_failure_callback: 'OnLoadFailureCallbackT[T] | None' = None,
        verify_requirements: bool | None = None,
        *,
        conflict_resolver: 'ConflictResolverT[T]' = ignore_conflicts,
    ) -> None:
        invoke_args = () if invoke_args is None else invoke_args
        invoke_kwds = {} if invoke_kwds is None else invoke_kwds

        if verify_requirements is not None:
            warnings.warn(
                'The verify_requirements argument is now a no-op and is '
                'deprecated for removal. Remove the argument from calls.',
                DeprecationWarning,
            )

        self.namespace = namespace
        self.propagate_map_exceptions = propagate_map_exceptions
        self._on_load_failure_callback = on_load_failure_callback
        self._conflict_resolver = conflict_resolver

        extensions = self._load_plugins(
            invoke_on_load, invoke_args, invoke_kwds
        )

        self._init_plugins(extensions)

    @classmethod
    def make_test_instance(
        cls,
        extensions: list[Extension[T]],
        namespace: str = 'TESTING',
        propagate_map_exceptions: bool = False,
        on_load_failure_callback: 'OnLoadFailureCallbackT[T] | None' = None,
        verify_requirements: bool | None = None,
        *,
        conflict_resolver: 'ConflictResolverT[T]' = ignore_conflicts,
    ) -> 'Self':
        """Construct a test ExtensionManager

        Test instances are passed a list of extensions to work from rather
        than loading them from entry points.

        :param extensions: Pre-configured Extension instances to use
        :param namespace: The namespace for the manager; used only for
            identification since the extensions are passed in.
        :param propagate_map_exceptions: When calling map, controls whether
            exceptions are propagated up through the map call or whether they
            are logged and then ignored
        :param on_load_failure_callback: Callback function that will
            be called when an entrypoint can not be loaded. The
            arguments that will be provided when this is called (when
            an entrypoint fails to load) are (manager, entrypoint,
            exception)
        :param verify_requirements: **DEPRECATED** This is a no-op and will be
            removed in a future version.
        :param conflict_resolver: A callable that determines what to do in the
            event that there are multiple entrypoints in the same group with
            the same name. This is only used if retrieving entrypoint by name.
        :return: The manager instance, initialized for testing
        """
        if verify_requirements is not None:
            warnings.warn(
                'The verify_requirements argument is now a no-op and is '
                'deprecated for removal. Remove the argument from calls.',
                DeprecationWarning,
            )

        o = cls.__new__(cls)
        o.namespace = namespace
        o.propagate_map_exceptions = propagate_map_exceptions
        o._on_load_failure_callback = on_load_failure_callback
        o._conflict_resolver = conflict_resolver
        o._init_plugins(extensions)
        return o

    def _init_plugins(self, extensions: list[Extension[T]]) -> None:
        self.extensions: list[Extension[T]] = extensions
        self._extensions_by_name_cache: dict[str, Extension[T]] | None = None

    @property
    def _extensions_by_name(self) -> dict[str, Extension[T]]:
        if self._extensions_by_name_cache is None:
            d = {}
            for name, _extensions in itertools.groupby(
                self.extensions, lambda x: x.name
            ):
                extensions = list(_extensions)
                if len(extensions) > 1:
                    ext = self._conflict_resolver(
                        self.namespace, name, extensions
                    )
                else:
                    ext = extensions[0]

                d[name] = ext

            self._extensions_by_name_cache = d
        return self._extensions_by_name_cache

    def list_entry_points(self) -> list[importlib.metadata.EntryPoint]:
        """Return the list of entry points for this namespace.

        The entry points are not actually loaded, their list is just read and
        returned.
        """
        if self.namespace not in self.ENTRY_POINT_CACHE:
            eps = list(_cache.get_group_all(self.namespace))
            self.ENTRY_POINT_CACHE[self.namespace] = eps
        return self.ENTRY_POINT_CACHE[self.namespace]

    def entry_points_names(self) -> list[str]:
        """Return the list of entry points names for this namespace."""
        return list(map(operator.attrgetter("name"), self.list_entry_points()))

    def _load_plugins(
        self,
        invoke_on_load: bool,
        invoke_args: tuple[Any, ...],
        invoke_kwds: dict[str, Any],
    ) -> list[Extension[T]]:
        extensions = []
        for ep in self.list_entry_points():
            LOG.debug('found extension %r', ep)
            try:
                ext = self._load_one_plugin(
                    ep, invoke_on_load, invoke_args, invoke_kwds
                )
                if ext:
                    extensions.append(ext)
            except (KeyboardInterrupt, AssertionError):
                raise
            except Exception as err:
                if self._on_load_failure_callback is not None:
                    self._on_load_failure_callback(self, ep, err)
                else:
                    # Log the reason we couldn't import the module,
                    # usually without a traceback. The most common
                    # reason is an ImportError due to a missing
                    # dependency, and the error message should be
                    # enough to debug that.  If debug logging is
                    # enabled for our logger, provide the full
                    # traceback.
                    LOG.error(
                        'Could not load %r: %s',
                        ep.name,
                        err,
                        exc_info=LOG.isEnabledFor(logging.DEBUG),
                    )
        return extensions

    # NOTE(stephenfin): While this can't return None, all the subclasses can,
    # and this allows us to satisfy Liskov's Principle. `_load_plugins` handles
    # things just fine in either case.
    def _load_one_plugin(
        self,
        ep: importlib.metadata.EntryPoint,
        invoke_on_load: bool,
        invoke_args: tuple[Any],
        invoke_kwds: dict[str, Any],
    ) -> Extension[T] | None:
        plugin = ep.load()
        if invoke_on_load:
            obj = plugin(*invoke_args, **invoke_kwds)
        else:
            obj = None
        return Extension(ep.name, ep, plugin, obj)

    def names(self) -> list[str]:
        """Returns the names of the discovered extensions"""
        # We want to return the names of the extensions in the order
        # they would be used by map(), since some subclasses change
        # that order.
        return [e.name for e in self.extensions]

    def map(
        self,
        func: Callable[Concatenate[Extension[T], P], U],
        *args: P.args,
        **kwds: P.kwargs,
    ) -> list[U]:
        """Iterate over the extensions invoking func() for each.

        The signature for func() should be::

            def func(ext, *args, **kwds):
                pass

        The first argument to func(), 'ext', is the
        :class:`~stevedore.extension.Extension` instance.

        Exceptions raised from within func() are propagated up and
        processing stopped if self.propagate_map_exceptions is True,
        otherwise they are logged and ignored.

        :param func: Callable to invoke for each extension.
        :param args: Variable arguments to pass to func()
        :param kwds: Keyword arguments to pass to func()
        :returns: List of values returned from func()
        """
        if not self.extensions:
            # FIXME: Use a more specific exception class here.
            raise NoMatches(f'No {self.namespace} extensions found')
        response: list[U] = []
        for e in self.extensions:
            self._invoke_one_plugin(response.append, func, e, *args, **kwds)
        return response

    @staticmethod
    def _call_extension_method(
        extension: Extension[T], /, method_name: str, *args: Any, **kwds: Any
    ) -> Any:
        return getattr(extension.obj, method_name)(*args, **kwds)

    def map_method(self, method_name: str, *args: Any, **kwds: Any) -> Any:
        """Iterate over the extensions invoking a method by name.

        This is equivalent of using :meth:`map` with func set to
        `lambda x: x.obj.method_name()`
        while being more convenient.

        Exceptions raised from within the called method are propagated up
        and processing stopped if self.propagate_map_exceptions is True,
        otherwise they are logged and ignored.

        .. versionadded:: 0.12

        :param method_name: The extension method name
                            to call for each extension.
        :param args: Variable arguments to pass to method
        :param kwds: Keyword arguments to pass to method
        :returns: List of values returned from methods
        """
        return self.map(
            self._call_extension_method, method_name, *args, **kwds
        )

    def _invoke_one_plugin(
        self,
        response_callback: Callable[..., Any],
        func: Callable[Concatenate[Extension[T], P], U],
        e: Extension[T],
        *args: P.args,
        **kwds: P.kwargs,
    ) -> None:
        try:
            response_callback(func(e, *args, **kwds))
        except Exception as err:
            if self.propagate_map_exceptions:
                raise
            else:
                LOG.error('error calling %r: %s', e.name, err)
                LOG.exception(err)

    def items(self) -> ItemsView[str, Extension[T]]:
        """Return an iterator of tuples of the form (name, extension).

        This is analogous to the Mapping.items() method.
        """
        return self._extensions_by_name.items()

    def __iter__(self) -> Iterator[Extension[T]]:
        """Produce iterator for the manager.

        Iterating over an ExtensionManager produces the :class:`Extension`
        instances in the order they would be invoked.
        """
        return iter(self.extensions)

    def __getitem__(self, name: str) -> Extension[T]:
        """Return the named extension.

        Accessing an ExtensionManager as a dictionary (``em['name']``)
        produces the :class:`Extension` instance with the specified name.
        """
        return self._extensions_by_name[name]

    def __contains__(self, name: str) -> bool:
        """Return true if name is in list of enabled extensions."""
        return any(extension.name == name for extension in self.extensions)
