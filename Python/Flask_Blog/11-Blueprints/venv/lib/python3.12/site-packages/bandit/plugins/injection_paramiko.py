#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
r"""
==============================================
B601: Test for shell injection within Paramiko
==============================================

Paramiko is a Python library designed to work with the SSH2 protocol for secure
(encrypted and authenticated) connections to remote machines. It is intended to
run commands on a remote host. These commands are run within a shell on the
target and are thus vulnerable to various shell injection attacks. Bandit
reports a MEDIUM issue when it detects the use of Paramiko's "exec_command"
method advising the user to check inputs are correctly sanitized.

:Example:

.. code-block:: none

    >> Issue: Possible shell injection via Paramiko call, check inputs are
       properly sanitized.
       Severity: Medium   Confidence: Medium
       CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
       Location: ./examples/paramiko_injection.py:4
    3    # this is not safe
    4    paramiko.exec_command('something; really; unsafe')
    5

.. seealso::

 - https://security.openstack.org
 - https://github.com/paramiko/paramiko
 - https://www.owasp.org/index.php/Command_Injection
 - https://cwe.mitre.org/data/definitions/78.html

.. versionadded:: 0.12.0

.. versionchanged:: 1.7.3
    CWE information added

"""
import bandit
from bandit.core import issue
from bandit.core import test_properties as test


@test.checks("Call")
@test.test_id("B601")
def paramiko_calls(context):
    issue_text = (
        "Possible shell injection via Paramiko call, check inputs "
        "are properly sanitized."
    )
    for module in ["paramiko"]:
        if context.is_module_imported_like(module):
            if context.call_function_name in ["exec_command"]:
                return bandit.Issue(
                    severity=bandit.MEDIUM,
                    confidence=bandit.MEDIUM,
                    cwe=issue.Cwe.OS_COMMAND_INJECTION,
                    text=issue_text,
                )
