#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
r"""
=========================================
B110: Test for a pass in the except block
=========================================

Errors in Python code bases are typically communicated using ``Exceptions``.
An exception object is 'raised' in the event of an error and can be 'caught' at
a later point in the program, typically some error handling or logging action
will then be performed.

However, it is possible to catch an exception and silently ignore it. This is
illustrated with the following example

.. code-block:: python

    try:
      do_some_stuff()
    except Exception:
      pass

This pattern is considered bad practice in general, but also represents a
potential security issue. A larger than normal volume of errors from a service
can indicate an attempt is being made to disrupt or interfere with it. Thus
errors should, at the very least, be logged.

There are rare situations where it is desirable to suppress errors, but this is
typically done with specific exception types, rather than the base Exception
class (or no type). To accommodate this, the test may be configured to ignore
'try, except, pass' where the exception is typed. For example, the following
would not generate a warning if the configuration option
``checked_typed_exception`` is set to False:

.. code-block:: python

    try:
      do_some_stuff()
    except ZeroDivisionError:
      pass

**Config Options:**

.. code-block:: yaml

    try_except_pass:
      check_typed_exception: True


:Example:

.. code-block:: none

    >> Issue: Try, Except, Pass detected.
       Severity: Low   Confidence: High
       CWE: CWE-703 (https://cwe.mitre.org/data/definitions/703.html)
       Location: ./examples/try_except_pass.py:4
    3        a = 1
    4    except:
    5        pass

.. seealso::

 - https://security.openstack.org
 - https://cwe.mitre.org/data/definitions/703.html

.. versionadded:: 0.13.0

.. versionchanged:: 1.7.3
    CWE information added

"""
import ast

import bandit
from bandit.core import issue
from bandit.core import test_properties as test


def gen_config(name):
    if name == "try_except_pass":
        return {"check_typed_exception": False}


@test.takes_config
@test.checks("ExceptHandler")
@test.test_id("B110")
def try_except_pass(context, config):
    node = context.node
    if len(node.body) == 1:
        if (
            not config["check_typed_exception"]
            and node.type is not None
            and getattr(node.type, "id", None) != "Exception"
        ):
            return

        if isinstance(node.body[0], ast.Pass):
            return bandit.Issue(
                severity=bandit.LOW,
                confidence=bandit.HIGH,
                cwe=issue.Cwe.IMPROPER_CHECK_OF_EXCEPT_COND,
                text=("Try, Except, Pass detected."),
            )
