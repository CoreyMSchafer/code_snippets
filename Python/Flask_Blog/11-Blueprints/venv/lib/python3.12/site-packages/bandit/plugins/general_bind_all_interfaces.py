#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
r"""
========================================
B104: Test for binding to all interfaces
========================================

Binding to all network interfaces can potentially open up a service to traffic
on unintended interfaces, that may not be properly documented or secured. This
plugin test looks for a string pattern "0.0.0.0" that may indicate a hardcoded
binding to all network interfaces.

:Example:

.. code-block:: none

    >> Issue: Possible binding to all interfaces.
       Severity: Medium   Confidence: Medium
       CWE: CWE-605 (https://cwe.mitre.org/data/definitions/605.html)
       Location: ./examples/binding.py:4
    3   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    4   s.bind(('0.0.0.0', 31137))
    5   s.bind(('192.168.0.1', 8080))

.. seealso::

 - https://nvd.nist.gov/vuln/detail/CVE-2018-1281
 - https://cwe.mitre.org/data/definitions/605.html

.. versionadded:: 0.9.0

.. versionchanged:: 1.7.3
    CWE information added

"""
import bandit
from bandit.core import issue
from bandit.core import test_properties as test


@test.checks("Str")
@test.test_id("B104")
def hardcoded_bind_all_interfaces(context):
    if context.string_val == "0.0.0.0":  # nosec: B104
        return bandit.Issue(
            severity=bandit.MEDIUM,
            confidence=bandit.MEDIUM,
            cwe=issue.Cwe.MULTIPLE_BINDS,
            text="Possible binding to all interfaces.",
        )
