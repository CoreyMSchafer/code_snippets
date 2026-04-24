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

from typing import Any
from typing import TypeVar

from .extension import ConflictResolverT
from .extension import Extension
from .extension import ignore_conflicts
from .extension import OnLoadFailureCallbackT
from .named import NamedExtensionManager
from .named import OnMissingEntrypointsCallbackT

T = TypeVar('T')


class HookManager(NamedExtensionManager[T]):
    """Coordinate execution of multiple extensions using a common name.

    :param namespace: The namespace for the entry points.
    :param name: The name of the hooks to load.
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
        # NOTE(dhellmann): This default is different from the
        # base class because for hooks it is less likely to
        # be an error to have no entry points present.
        on_missing_entrypoints_callback: (
            OnMissingEntrypointsCallbackT | None
        ) = None,
        verify_requirements: bool | None = None,
        warn_on_missing_entrypoint: bool | None = None,
        *,
        conflict_resolver: 'ConflictResolverT[T]' = ignore_conflicts,
    ):
        invoke_args = () if invoke_args is None else invoke_args
        invoke_kwds = {} if invoke_kwds is None else invoke_kwds

        super().__init__(
            namespace,
            [name],
            invoke_on_load=invoke_on_load,
            invoke_args=invoke_args,
            invoke_kwds=invoke_kwds,
            on_load_failure_callback=on_load_failure_callback,
            on_missing_entrypoints_callback=on_missing_entrypoints_callback,
            verify_requirements=verify_requirements,
            warn_on_missing_entrypoint=warn_on_missing_entrypoint,
        )

    @property
    def _name(self) -> str:
        return self._names[0]

    def __getitem__(  # type: ignore[override]
        self, name: str
    ) -> list[Extension[T]]:
        """Return the named extensions.

        Accessing a HookManager as a dictionary (``em['name']``)
        produces a list of the :class:`Extension` instance(s) with the
        specified name, in the order they would be invoked by map().
        """
        if name != self._name:
            raise KeyError(name)
        return self.extensions
