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

"""TestExtensionManager

Extension manager used only for testing.
"""

from typing import TypeVar
import warnings

from stevedore import extension

T = TypeVar('T')


class TestExtensionManager(extension.ExtensionManager[T]):
    """ExtensionManager that is explicitly initialized for tests.

    .. deprecated:: 0.13

       Use the :func:`make_test_instance` class method of the class
       being replaced by the test instance instead of using this class
       directly.

    :param extensions: Pre-configured Extension instances to use instead of
        loading them from entry points.
    :param namespace: The namespace for the entry points.
    :param invoke_on_load: Boolean controlling whether to invoke the
        object returned by the entry point after the driver is loaded.
    :param invoke_args: Positional arguments to pass when invoking
        the object returned by the entry point. Only used if invoke_on_load
        is True.
    :param invoke_kwds: Named arguments to pass when invoking
        the object returned by the entry point. Only used if invoke_on_load
        is True.
    """

    def __init__(
        self,
        extensions,
        namespace='test',
        invoke_on_load=False,
        invoke_args=(),
        invoke_kwds={},
    ):
        super().__init__(namespace, invoke_on_load, invoke_args, invoke_kwds)
        self.extensions = extensions
        warnings.warn(
            'TestExtesionManager has been replaced by make_test_instance()',
            DeprecationWarning,
        )

    def _load_plugins(self, *args, **kwds):
        return []
