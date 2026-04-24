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
from collections.abc import Iterable
from collections.abc import Sequence
import importlib.metadata
import logging
from typing import Any
from typing import TYPE_CHECKING
from typing import TypeVar
import warnings

from .extension import ConflictResolverT
from .extension import Extension
from .extension import ExtensionManager
from .extension import ignore_conflicts
from .extension import OnLoadFailureCallbackT

if TYPE_CHECKING:
    from typing_extensions import Self

LOG = logging.getLogger(__name__)

T = TypeVar('T')
OnMissingEntrypointsCallbackT = Callable[[Iterable[str]], None]


def warning_on_missing_entrypoint(missing_names: Iterable[str]) -> None:
    LOG.warning('Could not load %s', ', '.join(missing_names))


class NamedExtensionManager(ExtensionManager[T]):
    """Loads only the named extensions.

    This is useful for explicitly enabling extensions in a
    configuration file, for example.

    :param namespace: The namespace for the entry points.
    :param names: The names of the extensions to load.
    :param invoke_on_load: Boolean controlling whether to invoke the
        object returned by the entry point after the driver is loaded.
    :param invoke_args: Positional arguments to pass when invoking
        the object returned by the entry point. Only used if invoke_on_load
        is True.
    :param invoke_kwds: Named arguments to pass when invoking
        the object returned by the entry point. Only used if invoke_on_load
        is True.
    :param name_order: If true, sort the loaded extensions to match the
        order used in ``names``.
    :param propagate_map_exceptions: Boolean controlling whether exceptions
        are propagated up through the map call or whether they are logged and
        then ignored
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
        names: Sequence[str],
        invoke_on_load: bool = False,
        invoke_args: tuple[Any, ...] | None = None,
        invoke_kwds: dict[str, Any] | None = None,
        name_order: bool = False,
        propagate_map_exceptions: bool = False,
        on_load_failure_callback: 'OnLoadFailureCallbackT[T] | None' = None,
        on_missing_entrypoints_callback: (
            OnMissingEntrypointsCallbackT | None
        ) = warning_on_missing_entrypoint,
        verify_requirements: bool | None = None,
        warn_on_missing_entrypoint: bool | None = None,
        *,
        conflict_resolver: 'ConflictResolverT[T]' = ignore_conflicts,
    ) -> None:
        self._names = names
        self._missing_names: set[str] = set()
        self._name_order = name_order

        if warn_on_missing_entrypoint is not None:
            warnings.warn(
                "The warn_on_missing_entrypoint option is deprecated for "
                "removal. If you wish to disable warnings, you should instead "
                "override 'on_missing_entrypoints_callback'",
                DeprecationWarning,
            )
            if not warn_on_missing_entrypoint:
                on_missing_entrypoints_callback = None

        self._on_missing_entrypoints_callback = on_missing_entrypoints_callback

        super().__init__(
            namespace,
            invoke_on_load=invoke_on_load,
            invoke_args=invoke_args,
            invoke_kwds=invoke_kwds,
            propagate_map_exceptions=propagate_map_exceptions,
            on_load_failure_callback=on_load_failure_callback,
            verify_requirements=verify_requirements,
            conflict_resolver=conflict_resolver,
        )

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
        """Construct a test NamedExtensionManager

        Test instances are passed a list of extensions to use rather than
        loading them from entry points.

        :param extensions: Pre-configured Extension instances
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
        o._names = [e.name for e in extensions]
        o._missing_names = set()
        o._name_order = False
        o._conflict_resolver = conflict_resolver
        o._init_plugins(extensions)
        return o

    def _init_plugins(self, extensions: list[Extension[T]]) -> None:
        super()._init_plugins(extensions)

        if self._name_order:
            self.extensions = [
                self[n] for n in self._names if n not in self._missing_names
            ]

    def _load_plugins(
        self,
        invoke_on_load: bool,
        invoke_args: tuple[Any, ...],
        invoke_kwds: dict[str, Any],
    ) -> list[Extension[T]]:
        extensions = super()._load_plugins(
            invoke_on_load, invoke_args, invoke_kwds
        )

        self._missing_names = set(self._names) - {e.name for e in extensions}
        if self._missing_names and self._on_missing_entrypoints_callback:
            self._on_missing_entrypoints_callback(self._missing_names)

        return extensions

    def _load_one_plugin(
        self,
        ep: importlib.metadata.EntryPoint,
        invoke_on_load: bool,
        invoke_args: tuple[Any, ...],
        invoke_kwds: dict[str, Any],
    ) -> Extension[T] | None:
        # Check the name before going any further to prevent
        # undesirable code from being loaded at all if we are not
        # going to use it.
        if ep.name not in self._names:
            return None

        return super()._load_one_plugin(
            ep, invoke_on_load, invoke_args, invoke_kwds
        )
