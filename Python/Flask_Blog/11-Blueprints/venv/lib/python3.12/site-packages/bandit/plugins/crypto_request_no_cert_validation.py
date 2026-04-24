#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
r"""
=============================================
B501: Test for missing certificate validation
=============================================

Encryption in general is typically critical to the security of many
applications.  Using TLS can greatly increase security by guaranteeing the
identity of the party you are communicating with.  This is accomplished by one
or both parties presenting trusted certificates during the connection
initialization phase of TLS.

When HTTPS request methods are used, certificates are validated automatically
which is the desired behavior.  If certificate validation is explicitly turned
off Bandit will return a HIGH severity error.


:Example:

.. code-block:: none

    >> Issue: [request_with_no_cert_validation] Call to requests with
    verify=False disabling SSL certificate checks, security issue.
       Severity: High   Confidence: High
       CWE: CWE-295 (https://cwe.mitre.org/data/definitions/295.html)
       Location: examples/requests-ssl-verify-disabled.py:4
    3   requests.get('https://gmail.com', verify=True)
    4   requests.get('https://gmail.com', verify=False)
    5   requests.post('https://gmail.com', verify=True)

.. seealso::

 - https://security.openstack.org/guidelines/dg_move-data-securely.html
 - https://security.openstack.org/guidelines/dg_validate-certificates.html
 - https://cwe.mitre.org/data/definitions/295.html

.. versionadded:: 0.9.0

.. versionchanged:: 1.7.3
    CWE information added

.. versionchanged:: 1.7.5
    Added check for httpx module

"""
import bandit
from bandit.core import issue
from bandit.core import test_properties as test


@test.checks("Call")
@test.test_id("B501")
def request_with_no_cert_validation(context):
    HTTP_VERBS = {"get", "options", "head", "post", "put", "patch", "delete"}
    HTTPX_ATTRS = {"request", "stream", "Client", "AsyncClient"} | HTTP_VERBS
    qualname = context.call_function_name_qual.split(".")[0]

    if (
        qualname == "requests"
        and context.call_function_name in HTTP_VERBS
        or qualname == "httpx"
        and context.call_function_name in HTTPX_ATTRS
    ):
        if context.check_call_arg_value("verify", "False"):
            return bandit.Issue(
                severity=bandit.HIGH,
                confidence=bandit.HIGH,
                cwe=issue.Cwe.IMPROPER_CERT_VALIDATION,
                text=f"Call to {qualname} with verify=False disabling SSL "
                "certificate checks, security issue.",
                lineno=context.get_lineno_for_call_arg("verify"),
            )
