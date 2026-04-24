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
from collections.abc import Sequence
import logging
from typing import Any
from typing import Concatenate
from typing import ParamSpec
from typing import TypeVar

from .enabled import EnabledExtensionManager
from .exception import NoMatches
from .extension import Extension
from .extension import OnLoadFailureCallbackT

LOG = logging.getLogger(__name__)

T = TypeVar('T')
U = TypeVar('U')
P = ParamSpec('P')
Q = ParamSpec('Q')


class DispatchExtensionManager(EnabledExtensionManager[T]):
    """Loads all plugins and filters on execution.

    This is useful for long-running processes that need to pass
    different inputs to different extensions.

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
    """

    def map(  # type: ignore[override]
        self,
        filter_func: Callable[Concatenate[Extension[T], P], bool],
        func: Callable[Concatenate[Extension[T], Q], U],
        *args: Any,
        **kwds: Any,
    ) -> list[U]:
        """Iterate over the extensions invoking func() for any where
        filter_func() returns True.

        The signature of filter_func() should be::

            def filter_func(ext, *args, **kwds):
                pass

        The first argument to filter_func(), 'ext', is the
        :class:`~stevedore.extension.Extension`
        instance. filter_func() should return True if the extension
        should be invoked for the input arguments.

        The signature for func() should be::

            def func(ext, *args, **kwds):
                pass

        The first argument to func(), 'ext', is the
        :class:`~stevedore.extension.Extension` instance.

        Exceptions raised from within func() are propagated up and
        processing stopped if self.propagate_map_exceptions is True,
        otherwise they are logged and ignored.

        :param filter_func: Callable to test each extension.
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
            if filter_func(e, *args, **kwds):
                self._invoke_one_plugin(
                    response.append, func, e, *args, **kwds
                )
        return response

    def map_method(  # type: ignore[override]
        self,
        filter_func: Callable[Concatenate[Extension[T], P], bool],
        method_name: str,
        *args: Any,
        **kwds: Any,
    ) -> Any:
        """Iterate over the extensions invoking each one's object method called
        `method_name` for any where filter_func() returns True.

        This is equivalent of using :meth:`map` with func set to
        `lambda x: x.obj.method_name()`
        while being more convenient.

        Exceptions raised from within the called method are propagated up
        and processing stopped if self.propagate_map_exceptions is True,
        otherwise they are logged and ignored.

        .. versionadded:: 0.12

        :param filter_func: Callable to test each extension.
        :param method_name: The extension method name to call
                            for each extension.
        :param args: Variable arguments to pass to method
        :param kwds: Keyword arguments to pass to method
        :returns: List of values returned from methods
        """
        return self.map(
            filter_func,
            self._call_extension_method,
            method_name,
            *args,
            **kwds,
        )


class NameDispatchExtensionManager(DispatchExtensionManager[T]):
    """Loads all plugins and filters on execution.

    This is useful for long-running processes that need to pass
    different inputs to different extensions and can predict the name
    of the extensions before calling them.

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
    ):
        invoke_args = () if invoke_args is None else invoke_args
        invoke_kwds = {} if invoke_kwds is None else invoke_kwds
        super().__init__(
            namespace=namespace,
            check_func=check_func,
            invoke_on_load=invoke_on_load,
            invoke_args=invoke_args,
            invoke_kwds=invoke_kwds,
            propagate_map_exceptions=propagate_map_exceptions,
            on_load_failure_callback=on_load_failure_callback,
            verify_requirements=verify_requirements,
        )

    def _init_plugins(self, extensions: list[Extension[T]]) -> None:
        super()._init_plugins(extensions)
        self.by_name = {e.name: e for e in self.extensions}

    def map(  # type: ignore[override]
        self,
        names: Sequence[str],
        func: Callable[Concatenate[Extension[T], P], U],
        *args: P.args,
        **kwds: P.kwargs,
    ) -> list[U]:
        """Iterate over the extensions invoking func() for any where
        the name is in the given list of names.

        The signature for func() should be::

            def func(ext, *args, **kwds):
                pass

        The first argument to func(), 'ext', is the
        :class:`~stevedore.extension.Extension` instance.

        Exceptions raised from within func() are propagated up and
        processing stopped if self.propagate_map_exceptions is True,
        otherwise they are logged and ignored.

        :param names: List or set of name(s) of extension(s) to invoke.
        :param func: Callable to invoke for each extension.
        :param args: Variable arguments to pass to func()
        :param kwds: Keyword arguments to pass to func()
        :returns: List of values returned from func()
        """
        response: list[U] = []
        for name in names:
            try:
                e = self.by_name[name]
            except KeyError:
                LOG.debug('Missing extension %r being ignored', name)
            else:
                self._invoke_one_plugin(
                    response.append, func, e, *args, **kwds
                )
        return response

    def map_method(  # type: ignore[override]
        self, names: Sequence[str], method_name: str, *args: Any, **kwds: Any
    ) -> Any:
        """Iterate over the extensions invoking each one's object method called
        `method_name` for any where the name is in the given list of names.

        This is equivalent of using :meth:`map` with func set to
        `lambda x: x.obj.method_name()`
        while being more convenient.

        Exceptions raised from within the called method are propagated up
        and processing stopped if self.propagate_map_exceptions is True,
        otherwise they are logged and ignored.

        .. versionadded:: 0.12

        :param names: List or set of name(s) of extension(s) to invoke.
        :param method_name: The extension method name
                            to call for each extension.
        :param args: Variable arguments to pass to method
        :param kwds: Keyword arguments to pass to method
        :returns: List of values returned from methods
        """
        return self.map(
            names, self._call_extension_method, method_name, *args, **kwds
        )
