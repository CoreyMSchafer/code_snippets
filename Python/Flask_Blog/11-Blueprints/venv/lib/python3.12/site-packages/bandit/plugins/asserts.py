#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
r"""
============================
B101: Test for use of assert
============================

This plugin test checks for the use of the Python ``assert`` keyword. It was
discovered that some projects used assert to enforce interface constraints.
However, assert is removed with compiling to optimised byte code (`python -O`
producing \*.opt-1.pyc files). This caused various protections to be removed.
Consider raising a semantically meaningful error or ``AssertionError`` instead.

Please see
https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement for
more info on ``assert``.

**Config Options:**

You can configure files that skip this check. This is often useful when you
use assert statements in test cases.

.. code-block:: yaml

    assert_used:
      skips: ['*_test.py', '*test_*.py']

:Example:

.. code-block:: none

    >> Issue: Use of assert detected. The enclosed code will be removed when
       compiling to optimised byte code.
       Severity: Low   Confidence: High
       CWE: CWE-703 (https://cwe.mitre.org/data/definitions/703.html)
       Location: ./examples/assert.py:1
    1 assert logged_in
    2 display_assets()

.. seealso::

 - https://bugs.launchpad.net/juniperopenstack/+bug/1456193
 - https://bugs.launchpad.net/heat/+bug/1397883
 - https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement
 - https://cwe.mitre.org/data/definitions/703.html

.. versionadded:: 0.11.0

.. versionchanged:: 1.7.3
    CWE information added

"""
import fnmatch

import bandit
from bandit.core import issue
from bandit.core import test_properties as test


def gen_config(name):
    if name == "assert_used":
        return {"skips": []}


@test.takes_config
@test.test_id("B101")
@test.checks("Assert")
def assert_used(context, config):
    for skip in config.get("skips", []):
        if fnmatch.fnmatch(context.filename, skip):
            return None

    return bandit.Issue(
        severity=bandit.LOW,
        confidence=bandit.HIGH,
        cwe=issue.Cwe.IMPROPER_CHECK_OF_EXCEPT_COND,
        text=(
            "Use of assert detected. The enclosed code "
            "will be removed when compiling to optimised byte code."
        ),
    )
