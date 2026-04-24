# Copyright (c) 2018 VMware, Inc.
#
# SPDX-License-Identifier: Apache-2.0
r"""
==========================================
B507: Test for missing host key validation
==========================================

Encryption in general is typically critical to the security of many
applications.  Using SSH can greatly increase security by guaranteeing the
identity of the party you are communicating with.  This is accomplished by one
or both parties presenting trusted host keys during the connection
initialization phase of SSH.

When paramiko methods are used, host keys are verified by default. If host key
verification is disabled, Bandit will return a HIGH severity error.

:Example:

.. code-block:: none

    >> Issue: [B507:ssh_no_host_key_verification] Paramiko call with policy set
    to automatically trust the unknown host key.
    Severity: High   Confidence: Medium
    CWE: CWE-295 (https://cwe.mitre.org/data/definitions/295.html)
    Location: examples/no_host_key_verification.py:4
    3   ssh_client = client.SSHClient()
    4   ssh_client.set_missing_host_key_policy(client.AutoAddPolicy)
    5   ssh_client.set_missing_host_key_policy(client.WarningPolicy)


.. versionadded:: 1.5.1

.. versionchanged:: 1.7.3
    CWE information added

"""
import ast

import bandit
from bandit.core import issue
from bandit.core import test_properties as test


@test.checks("Call")
@test.test_id("B507")
def ssh_no_host_key_verification(context):
    if (
        context.is_module_imported_like("paramiko")
        and context.call_function_name == "set_missing_host_key_policy"
        and context.node.args
    ):
        policy_argument = context.node.args[0]

        policy_argument_value = None
        if isinstance(policy_argument, ast.Attribute):
            policy_argument_value = policy_argument.attr
        elif isinstance(policy_argument, ast.Name):
            policy_argument_value = policy_argument.id
        elif isinstance(policy_argument, ast.Call):
            if isinstance(policy_argument.func, ast.Attribute):
                policy_argument_value = policy_argument.func.attr
            elif isinstance(policy_argument.func, ast.Name):
                policy_argument_value = policy_argument.func.id

        if policy_argument_value in ["AutoAddPolicy", "WarningPolicy"]:
            return bandit.Issue(
                severity=bandit.HIGH,
                confidence=bandit.MEDIUM,
                cwe=issue.Cwe.IMPROPER_CERT_VALIDATION,
                text="Paramiko call with policy set to automatically trust "
                "the unknown host key.",
                lineno=context.get_lineno_for_call_arg(
                    "set_missing_host_key_policy"
                ),
            )
