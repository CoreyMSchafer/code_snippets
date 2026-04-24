# SPDX-License-Identifier: Apache-2.0
r"""
=======================================
B113: Test for missing requests timeout
=======================================

This plugin test checks for ``requests`` or ``httpx`` calls without a timeout
specified.

Nearly all production code should use this parameter in nearly all requests,
Failure to do so can cause your program to hang indefinitely.

When request methods are used without the timeout parameter set,
Bandit will return a MEDIUM severity error.


:Example:

.. code-block:: none

    >> Issue: [B113:request_without_timeout] Call to requests without timeout
       Severity: Medium   Confidence: Low
       CWE: CWE-400 (https://cwe.mitre.org/data/definitions/400.html)
       More Info: https://bandit.readthedocs.io/en/latest/plugins/b113_request_without_timeout.html
       Location: examples/requests-missing-timeout.py:3:0
    2
    3	requests.get('https://gmail.com')
    4	requests.get('https://gmail.com', timeout=None)

    --------------------------------------------------
    >> Issue: [B113:request_without_timeout] Call to requests with timeout set to None
       Severity: Medium   Confidence: Low
       CWE: CWE-400 (https://cwe.mitre.org/data/definitions/400.html)
       More Info: https://bandit.readthedocs.io/en/latest/plugins/b113_request_without_timeout.html
       Location: examples/requests-missing-timeout.py:4:0
    3	requests.get('https://gmail.com')
    4	requests.get('https://gmail.com', timeout=None)
    5	requests.get('https://gmail.com', timeout=5)

.. seealso::

 - https://requests.readthedocs.io/en/latest/user/advanced/#timeouts

.. versionadded:: 1.7.5

.. versionchanged:: 1.7.10
    Added check for httpx module

"""  # noqa: E501
import bandit
from bandit.core import issue
from bandit.core import test_properties as test


@test.checks("Call")
@test.test_id("B113")
def request_without_timeout(context):
    HTTP_VERBS = {"get", "options", "head", "post", "put", "patch", "delete"}
    HTTPX_ATTRS = {"request", "stream", "Client", "AsyncClient"} | HTTP_VERBS
    qualname = context.call_function_name_qual.split(".")[0]

    if qualname == "requests" and context.call_function_name in HTTP_VERBS:
        # check for missing timeout
        if context.check_call_arg_value("timeout") is None:
            return bandit.Issue(
                severity=bandit.MEDIUM,
                confidence=bandit.LOW,
                cwe=issue.Cwe.UNCONTROLLED_RESOURCE_CONSUMPTION,
                text=f"Call to {qualname} without timeout",
            )
    if (
        qualname == "requests"
        and context.call_function_name in HTTP_VERBS
        or qualname == "httpx"
        and context.call_function_name in HTTPX_ATTRS
    ):
        # check for timeout=None
        if context.check_call_arg_value("timeout", "None"):
            return bandit.Issue(
                severity=bandit.MEDIUM,
                confidence=bandit.LOW,
                cwe=issue.Cwe.UNCONTROLLED_RESOURCE_CONSUMPTION,
                text=f"Call to {qualname} with timeout set to None",
            )
