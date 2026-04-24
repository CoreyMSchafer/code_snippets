#
# Copyright (c) 2016 Rackspace, Inc.
#
# SPDX-License-Identifier: Apache-2.0
r"""
===============================
B506: Test for use of yaml load
===============================

This plugin test checks for the unsafe usage of the ``yaml.load`` function from
the PyYAML package. The yaml.load function provides the ability to construct
an arbitrary Python object, which may be dangerous if you receive a YAML
document from an untrusted source. The function yaml.safe_load limits this
ability to simple Python objects like integers or lists.

Please see
https://pyyaml.org/wiki/PyYAMLDocumentation#LoadingYAML for more information
on ``yaml.load`` and yaml.safe_load

:Example:

.. code-block:: none

    >> Issue: [yaml_load] Use of unsafe yaml load. Allows instantiation of
       arbitrary objects. Consider yaml.safe_load().
       Severity: Medium   Confidence: High
       CWE: CWE-20 (https://cwe.mitre.org/data/definitions/20.html)
       Location: examples/yaml_load.py:5
    4 ystr = yaml.dump({'a' : 1, 'b' : 2, 'c' : 3})
    5 y = yaml.load(ystr)
    6 yaml.dump(y)

.. seealso::

 - https://pyyaml.org/wiki/PyYAMLDocumentation#LoadingYAML
 - https://cwe.mitre.org/data/definitions/20.html

.. versionadded:: 1.0.0

.. versionchanged:: 1.7.3
    CWE information added

"""
import bandit
from bandit.core import issue
from bandit.core import test_properties as test


@test.test_id("B506")
@test.checks("Call")
def yaml_load(context):
    imported = context.is_module_imported_exact("yaml")
    qualname = context.call_function_name_qual
    if not imported and isinstance(qualname, str):
        return

    qualname_list = qualname.split(".")
    func = qualname_list[-1]
    if all(
        [
            "yaml" in qualname_list,
            func == "load",
            not context.check_call_arg_value("Loader", "SafeLoader"),
            not context.check_call_arg_value("Loader", "CSafeLoader"),
            not context.get_call_arg_at_position(1) == "SafeLoader",
            not context.get_call_arg_at_position(1) == "CSafeLoader",
        ]
    ):
        return bandit.Issue(
            severity=bandit.MEDIUM,
            confidence=bandit.HIGH,
            cwe=issue.Cwe.IMPROPER_INPUT_VALIDATION,
            text="Use of unsafe yaml load. Allows instantiation of"
            " arbitrary objects. Consider yaml.safe_load().",
            lineno=context.node.lineno,
        )
