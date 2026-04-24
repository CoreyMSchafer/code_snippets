#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
r"""
==============================
B102: Test for the use of exec
==============================

This plugin test checks for the use of Python's `exec` method or keyword. The
Python docs succinctly describe why the use of `exec` is risky.

:Example:

.. code-block:: none

    >> Issue: Use of exec detected.
       Severity: Medium   Confidence: High
       CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
       Location: ./examples/exec.py:2
    1 exec("do evil")


.. seealso::

 - https://docs.python.org/3/library/functions.html#exec
 - https://www.python.org/dev/peps/pep-0551/#background
 - https://www.python.org/dev/peps/pep-0578/#suggested-audit-hook-locations
 - https://cwe.mitre.org/data/definitions/78.html

.. versionadded:: 0.9.0

.. versionchanged:: 1.7.3
    CWE information added

"""
import bandit
from bandit.core import issue
from bandit.core import test_properties as test


def exec_issue():
    return bandit.Issue(
        severity=bandit.MEDIUM,
        confidence=bandit.HIGH,
        cwe=issue.Cwe.OS_COMMAND_INJECTION,
        text="Use of exec detected.",
    )


@test.checks("Call")
@test.test_id("B102")
def exec_used(context):
    if context.call_function_name_qual == "exec":
        return exec_issue()
