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

from collections.abc import Callable
import importlib.metadata
from typing import Any
from typing import Concatenate
from typing import ParamSpec
from typing import TYPE_CHECKING
from typing import TypeVar

from .exception import MultipleMatches
from .exception import NoMatches
from .extension import ConflictResolverT
from .extension import Extension
from .extension import ExtensionManager
from .extension import ignore_conflicts
from .extension import OnLoadFailureCallbackT
from .named import NamedExtensionManager
from .named import OnMissingEntrypointsCallbackT
from .named import warning_on_missing_entrypoint

if TYPE_CHECKING:
    from typing_extensions import Self

T = TypeVar('T')
U = TypeVar('U')
P = ParamSpec('P')


class DriverManager(NamedExtensionManager[T]):
    """Load a single plugin with a given name from the namespace.

    :param namespace: The namespace for the entry points.
    :param name: The name of the driver to load.
    :param invoke_on_load: Boolean controlling whether to invoke the
        object returned by the entry point after the driver is loaded.
    :param invoke_args: Positional arguments to pass when invoking
        the object returned by the entry point. Only used if invoke_on_load
        is True.
    :param invoke_kwds: Named arguments to pass when invoking
        the object returned by the entry point. Only used if invoke_on_load
        is True.
    :param on_load_failure_callback: Callback function that will be called when
        an entrypoint can not be loaded. The arguments that will be provided
        when this is called (when an entrypoint fails to load) are
        (manager, entrypoint, exception)
    :param on_missing_entrypoints_callback: Callback function that will be
        called when one or more names cannot be found. The provided argument
        will be a subset of the 'names' parameter.
    :param verify_requirements: **DEPRECATED** This is a no-op and will be
        removed in a future version.
    :param warn_on_missing_entrypoint: **DEPRECATED** Flag to control whether
        failing to load a plugin is reported via a log mess. Only applies if
        on_missing_entrypoints_callback is None. Users should instead set
        ``on_missing_entrypoints_callback`` to ``None`` if they wish to disable
        logging.
    :param conflict_resolver: A callable that determines what to do in the
        event that there are multiple entrypoints in the same group with the
        same name. This is only used if retrieving entrypoint by name.
    """

    def __init__(
        self,
        namespace: str,
        name: str,
        invoke_on_load: bool = False,
        invoke_args: tuple[Any, ...] | None = None,
        invoke_kwds: dict[str, Any] | None = None,
        on_load_failure_callback: 'OnLoadFailureCallbackT[T] | None' = None,
        on_missing_entrypoints_callback: (
            OnMissingEntrypointsCallbackT | None
        ) = warning_on_missing_entrypoint,
        verify_requirements: bool | None = None,
        warn_on_missing_entrypoint: bool | None = None,
        *,
        conflict_resolver: 'ConflictResolverT[T]' = ignore_conflicts,
    ) -> None:
        invoke_args = () if invoke_args is None else invoke_args
        invoke_kwds = {} if invoke_kwds is None else invoke_kwds
        on_load_failure_callback = (
            on_load_failure_callback or self._default_on_load_failure
        )

        super().__init__(
            namespace=namespace,
            names=[name],
            invoke_on_load=invoke_on_load,
            invoke_args=invoke_args,
            invoke_kwds=invoke_kwds,
            on_load_failure_callback=on_load_failure_callback,
            verify_requirements=verify_requirements,
            warn_on_missing_entrypoint=warn_on_missing_entrypoint,
            conflict_resolver=conflict_resolver,
        )

    @staticmethod
    def _default_on_load_failure(
        manager: 'ExtensionManager[T]',
        ep: importlib.metadata.EntryPoint,
        err: BaseException,
    ) -> None:
        raise

    @classmethod
    def make_test_instance(  # type: ignore[override]
        cls,
        extension: Extension[T],
        namespace: str = 'TESTING',
        propagate_map_exceptions: bool = False,
        on_load_failure_callback: 'OnLoadFailureCallbackT[T] | None' = None,
        verify_requirements: bool | None = None,
        *,
        conflict_resolver: 'ConflictResolverT[T]' = ignore_conflicts,
    ) -> 'Self':
        """Construct a test DriverManager

        Test instances are passed a list of extensions to work from rather
        than loading them from entry points.

        :param extension: Pre-configured Extension instance
        :param namespace: The namespace for the manager; used only for
            identification since the extensions are passed in.
        :param propagate_map_exceptions: Boolean controlling whether exceptions
            are propagated up through the map call or whether they are logged
            and then ignored
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
        o = super().make_test_instance(
            [extension],
            namespace=namespace,
            propagate_map_exceptions=propagate_map_exceptions,
            on_load_failure_callback=on_load_failure_callback,
            verify_requirements=verify_requirements,
            conflict_resolver=conflict_resolver,
        )
        return o

    def _init_plugins(self, extensions: list[Extension[T]]) -> None:
        super()._init_plugins(extensions)

        if not self.extensions:
            name = self._names[0]
            raise NoMatches(
                f'No {self.namespace!r} driver found, looking for {name!r}'
            )
        if len(self.extensions) > 1:
            discovered_drivers = ','.join(
                e.entry_point_target for e in self.extensions
            )

            raise MultipleMatches(
                f'Multiple {self.namespace!r} drivers found: '
                f'{discovered_drivers}'
            )

    def __call__(
        self,
        func: Callable[Concatenate[Extension[T], P], U],
        *args: Any,
        **kwds: Any,
    ) -> U | None:
        """Invokes func() for the single loaded extension.

        The signature for func() should be::

            def func(ext, *args, **kwds):
                pass

        The first argument to func(), 'ext', is the
        :class:`~stevedore.extension.Extension` instance.

        Exceptions raised from within func() are logged and ignored.

        :param func: Callable to invoke for each extension.
        :param args: Variable arguments to pass to func()
        :param kwds: Keyword arguments to pass to func()
        :returns: List of values returned from func()
        """
        results = self.map(func, *args, **kwds)
        if results:
            return results[0]
        return None

    @property
    def driver(self) -> T | Callable[..., T]:
        """Returns the driver being used by this manager."""
        ext = self.extensions[0]
        return ext.obj if ext.obj else ext.plugin
