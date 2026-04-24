# Copyright (C) 2020 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
from collections.abc import Iterable
from typing import Any

from stevedore import extension

from .base import FormatterBase


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--width', default=60, type=int, help='maximum output width for text'
    )
    parsed_args = parser.parse_args()

    data = {'a': 'A', 'b': 'B', 'long': 'word ' * 80}

    mgr: extension.ExtensionManager[FormatterBase]
    mgr = extension.ExtensionManager(
        namespace='stevedore.example.formatter',
        invoke_on_load=True,
        invoke_args=(parsed_args.width,),
    )

    def format_data(
        ext: extension.Extension[FormatterBase], data: dict[str, Any], /
    ) -> tuple[str, Iterable[str]]:
        assert ext.obj is not None
        return (ext.name, ext.obj.format(data))

    results = mgr.map(format_data, data)

    for name, result in results:
        print(f'Formatter: {name}')
        for chunk in result:
            print(chunk, end='')
        print('')
