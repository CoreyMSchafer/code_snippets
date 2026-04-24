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
import logging
from typing import Any
from typing import TypeVar

from .extension import ConflictResolverT
from .extension import Extension
from .extension import ExtensionManager
from .extension import ignore_conflicts
from .extension import OnLoadFailureCallbackT

LOG = logging.getLogger(__name__)

T = TypeVar('T')


class EnabledExtensionManager(ExtensionManager[T]):
    """Loads only plugins that pass a check function.

    The check_func argument should return a boolean, with ``True``
    indicating that the extension should be loaded and made available
    and ``False`` indicating that the extension should be ignored.

    :param namespace: The namespace for the entry points.
    :param check_func: Function to determine which extensions to load.
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

    def __init__(
        self,
        namespace: str,
        check_func: Callable[[Extension[T]], bool],
        invoke_on_load: bool = False,
        invoke_args: tuple[Any, ...] | None = None,
        invoke_kwds: dict[str, Any] | None = None,
        propagate_map_exceptions: bool = False,
        on_load_failure_callback: 'OnLoadFailureCallbackT[T] | None' = None,
        verify_requirements: bool | None = None,
        *,
        conflict_resolver: 'ConflictResolverT[T]' = ignore_conflicts,
    ):
        invoke_args = () if invoke_args is None else invoke_args
        invoke_kwds = {} if invoke_kwds is None else invoke_kwds

        self.check_func = check_func

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

    def _load_one_plugin(
        self,
        ep: importlib.metadata.EntryPoint,
        invoke_on_load: bool,
        invoke_args: tuple[Any, ...],
        invoke_kwds: dict[str, Any],
    ) -> Extension[T] | None:
        ext = super()._load_one_plugin(
            ep, invoke_on_load, invoke_args, invoke_kwds
        )
        if ext and not self.check_func(ext):
            LOG.debug('ignoring extension %r', ep.name)
            return None
        return ext
