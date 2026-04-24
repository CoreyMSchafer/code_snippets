#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Sequence
import importlib.metadata
import inspect
from typing import Any
from typing import TypeVar

from docutils import nodes
from docutils.parsers import rst
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from sphinx.application import Sphinx
from sphinx.util import logging
from sphinx.util.nodes import nested_parse_with_titles

from stevedore import extension

LOG = logging.getLogger(__name__)

T = TypeVar('T')


def _get_docstring(plugin: Callable[..., T]) -> str:
    return inspect.getdoc(plugin) or ''


def _simple_list(
    mgr: extension.ExtensionManager[T],
) -> Iterable[tuple[str, str]]:
    for name in sorted(mgr.names()):
        ext = mgr[name]
        doc = _get_docstring(ext.plugin) or '\n'
        summary = doc.splitlines()[0].strip()
        yield (f'* {ext.name} -- {summary}', ext.module_name)


def _detailed_list(
    mgr: extension.ExtensionManager[T],
    over: str = '',
    under: str = '-',
    titlecase: bool = False,
) -> Iterable[tuple[str, str]]:
    for name in sorted(mgr.names()):
        ext = mgr[name]
        if over:
            yield (over * len(ext.name), ext.module_name)
        if titlecase:
            yield (ext.name.title(), ext.module_name)
        else:
            yield (ext.name, ext.module_name)
        if under:
            yield (under * len(ext.name), ext.module_name)
        yield ('\n', ext.module_name)
        doc = _get_docstring(ext.plugin)
        if doc:
            yield (doc, ext.module_name)
        else:
            yield (
                f'.. warning:: No documentation found for {ext.name} in '
                f'{ext.entry_point_target}',
                ext.module_name,
            )
        yield ('\n', ext.module_name)


class ListPluginsDirective(rst.Directive):
    """Present a simple list of the plugins in a namespace."""

    option_spec = {
        'class': directives.class_option,
        'detailed': directives.flag,
        'titlecase': directives.flag,
        'overline-style': directives.single_char_or_unicode,
        'underline-style': directives.single_char_or_unicode,
    }

    has_content = True

    def run(self) -> Sequence[nodes.Node]:
        namespace = ' '.join(self.content).strip()
        LOG.info('documenting plugins from %r', namespace)
        overline_style = self.options.get('overline-style', '')
        underline_style = self.options.get('underline-style', '=')

        def report_load_failure(
            mgr: extension.ExtensionManager[T],
            ep: importlib.metadata.EntryPoint,
            err: BaseException,
        ) -> None:
            LOG.warning('Failed to load %s: %s', ep.module, err)

        mgr: extension.ExtensionManager[Any]
        mgr = extension.ExtensionManager(
            namespace, on_load_failure_callback=report_load_failure
        )

        result = StringList()

        titlecase = 'titlecase' in self.options

        if 'detailed' in self.options:
            data = _detailed_list(
                mgr,
                over=overline_style,
                under=underline_style,
                titlecase=titlecase,
            )
        else:
            data = _simple_list(mgr)
        for text, source in data:
            for line in text.splitlines():
                result.append(line, source)

        # Parse what we have into a new section.
        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, result, node)

        return node.children


def setup(app: Sphinx) -> dict[str, Any]:
    LOG.info('loading stevedore.sphinxext')
    app.add_directive('list-plugins', ListPluginsDirective)
    return {'parallel_read_safe': True, 'parallel_write_safe': True}
