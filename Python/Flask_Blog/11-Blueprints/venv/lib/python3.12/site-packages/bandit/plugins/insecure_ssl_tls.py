#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
import bandit
from bandit.core import issue
from bandit.core import test_properties as test


def get_bad_proto_versions(config):
    return config["bad_protocol_versions"]


def gen_config(name):
    if name == "ssl_with_bad_version":
        return {
            "bad_protocol_versions": [
                "PROTOCOL_SSLv2",
                "SSLv2_METHOD",
                "SSLv23_METHOD",
                "PROTOCOL_SSLv3",  # strict option
                "PROTOCOL_TLSv1",  # strict option
                "SSLv3_METHOD",  # strict option
                "TLSv1_METHOD",
                "PROTOCOL_TLSv1_1",
                "TLSv1_1_METHOD",
            ]
        }  # strict option


@test.takes_config
@test.checks("Call")
@test.test_id("B502")
def ssl_with_bad_version(context, config):
    """**B502: Test for SSL use with bad version used**

    Several highly publicized exploitable flaws have been discovered
    in all versions of SSL and early versions of TLS. It is strongly
    recommended that use of the following known broken protocol versions be
    avoided:

    - SSL v2
    - SSL v3
    - TLS v1
    - TLS v1.1

    This plugin test scans for calls to Python methods with parameters that
    indicate the used broken SSL/TLS protocol versions. Currently, detection
    supports methods using Python's native SSL/TLS support and the pyOpenSSL
    module. A HIGH severity warning will be reported whenever known broken
    protocol versions are detected.

    It is worth noting that native support for TLS 1.2 is only available in
    more recent Python versions, specifically 2.7.9 and up, and 3.x

    A note on 'SSLv23':

    Amongst the available SSL/TLS versions provided by Python/pyOpenSSL there
    exists the option to use SSLv23. This very poorly named option actually
    means "use the highest version of SSL/TLS supported by both the server and
    client". This may (and should be) a version well in advance of SSL v2 or
    v3. Bandit can scan for the use of SSLv23 if desired, but its detection
    does not necessarily indicate a problem.

    When using SSLv23 it is important to also provide flags to explicitly
    exclude bad versions of SSL/TLS from the protocol versions considered. Both
    the Python native and pyOpenSSL modules provide the ``OP_NO_SSLv2`` and
    ``OP_NO_SSLv3`` flags for this purpose.

    **Config Options:**

    .. code-block:: yaml

        ssl_with_bad_version:
            bad_protocol_versions:
                - PROTOCOL_SSLv2
                - SSLv2_METHOD
                - SSLv23_METHOD
                - PROTOCOL_SSLv3  # strict option
                - PROTOCOL_TLSv1  # strict option
                - SSLv3_METHOD    # strict option
                - TLSv1_METHOD    # strict option

    :Example:

    .. code-block:: none

        >> Issue: ssl.wrap_socket call with insecure SSL/TLS protocol version
        identified, security issue.
           Severity: High   Confidence: High
           CWE: CWE-327 (https://cwe.mitre.org/data/definitions/327.html)
           Location: ./examples/ssl-insecure-version.py:13
        12  # strict tests
        13  ssl.wrap_socket(ssl_version=ssl.PROTOCOL_SSLv3)
        14  ssl.wrap_socket(ssl_version=ssl.PROTOCOL_TLSv1)

    .. seealso::

     - :func:`ssl_with_bad_defaults`
     - :func:`ssl_with_no_version`
     - https://heartbleed.com/
     - https://en.wikipedia.org/wiki/POODLE
     - https://security.openstack.org/guidelines/dg_move-data-securely.html
     - https://cwe.mitre.org/data/definitions/327.html

    .. versionadded:: 0.9.0

    .. versionchanged:: 1.7.3
        CWE information added

    .. versionchanged:: 1.7.5
        Added TLS 1.1

    """
    bad_ssl_versions = get_bad_proto_versions(config)
    if context.call_function_name_qual == "ssl.wrap_socket":
        if context.check_call_arg_value("ssl_version", bad_ssl_versions):
            return bandit.Issue(
                severity=bandit.HIGH,
                confidence=bandit.HIGH,
                cwe=issue.Cwe.BROKEN_CRYPTO,
                text="ssl.wrap_socket call with insecure SSL/TLS protocol "
                "version identified, security issue.",
                lineno=context.get_lineno_for_call_arg("ssl_version"),
            )
    elif context.call_function_name_qual == "pyOpenSSL.SSL.Context":
        if context.check_call_arg_value("method", bad_ssl_versions):
            return bandit.Issue(
                severity=bandit.HIGH,
                confidence=bandit.HIGH,
                cwe=issue.Cwe.BROKEN_CRYPTO,
                text="SSL.Context call with insecure SSL/TLS protocol "
                "version identified, security issue.",
                lineno=context.get_lineno_for_call_arg("method"),
            )

    elif (
        context.call_function_name_qual != "ssl.wrap_socket"
        and context.call_function_name_qual != "pyOpenSSL.SSL.Context"
    ):
        if context.check_call_arg_value(
            "method", bad_ssl_versions
        ) or context.check_call_arg_value("ssl_version", bad_ssl_versions):
            lineno = context.get_lineno_for_call_arg(
                "method"
            ) or context.get_lineno_for_call_arg("ssl_version")
            return bandit.Issue(
                severity=bandit.MEDIUM,
                confidence=bandit.MEDIUM,
                cwe=issue.Cwe.BROKEN_CRYPTO,
                text="Function call with insecure SSL/TLS protocol "
                "identified, possible security issue.",
                lineno=lineno,
            )


@test.takes_config("ssl_with_bad_version")
@test.checks("FunctionDef")
@test.test_id("B503")
def ssl_with_bad_defaults(context, config):
    """**B503: Test for SSL use with bad defaults specified**

    This plugin is part of a family of tests that detect the use of known bad
    versions of SSL/TLS, please see :doc:`../plugins/ssl_with_bad_version` for
    a complete discussion. Specifically, this plugin test scans for Python
    methods with default parameter values that specify the use of broken
    SSL/TLS protocol versions. Currently, detection supports methods using
    Python's native SSL/TLS support and the pyOpenSSL module. A MEDIUM severity
    warning will be reported whenever known broken protocol versions are
    detected.

    **Config Options:**

    This test shares the configuration provided for the standard
    :doc:`../plugins/ssl_with_bad_version` test, please refer to its
    documentation.

    :Example:

    .. code-block:: none

        >> Issue: Function definition identified with insecure SSL/TLS protocol
        version by default, possible security issue.
           Severity: Medium   Confidence: Medium
           CWE: CWE-327 (https://cwe.mitre.org/data/definitions/327.html)
           Location: ./examples/ssl-insecure-version.py:28
        27
        28  def open_ssl_socket(version=SSL.SSLv2_METHOD):
        29      pass

    .. seealso::

     - :func:`ssl_with_bad_version`
     - :func:`ssl_with_no_version`
     - https://heartbleed.com/
     - https://en.wikipedia.org/wiki/POODLE
     - https://security.openstack.org/guidelines/dg_move-data-securely.html

    .. versionadded:: 0.9.0

    .. versionchanged:: 1.7.3
        CWE information added

    .. versionchanged:: 1.7.5
        Added TLS 1.1

    """

    bad_ssl_versions = get_bad_proto_versions(config)
    for default in context.function_def_defaults_qual:
        val = default.split(".")[-1]
        if val in bad_ssl_versions:
            return bandit.Issue(
                severity=bandit.MEDIUM,
                confidence=bandit.MEDIUM,
                cwe=issue.Cwe.BROKEN_CRYPTO,
                text="Function definition identified with insecure SSL/TLS "
                "protocol version by default, possible security "
                "issue.",
            )


@test.checks("Call")
@test.test_id("B504")
def ssl_with_no_version(context):
    """**B504: Test for SSL use with no version specified**

    This plugin is part of a family of tests that detect the use of known bad
    versions of SSL/TLS, please see :doc:`../plugins/ssl_with_bad_version` for
    a complete discussion. Specifically, This plugin test scans for specific
    methods in Python's native SSL/TLS support and the pyOpenSSL module that
    configure the version of SSL/TLS protocol to use. These methods are known
    to provide default value that maximize compatibility, but permit use of the
    aforementioned broken protocol versions. A LOW severity warning will be
    reported whenever this is detected.

    **Config Options:**

    This test shares the configuration provided for the standard
    :doc:`../plugins/ssl_with_bad_version` test, please refer to its
    documentation.

    :Example:

    .. code-block:: none

        >> Issue: ssl.wrap_socket call with no SSL/TLS protocol version
        specified, the default SSLv23 could be insecure, possible security
        issue.
           Severity: Low   Confidence: Medium
           CWE: CWE-327 (https://cwe.mitre.org/data/definitions/327.html)
           Location: ./examples/ssl-insecure-version.py:23
        22
        23  ssl.wrap_socket()
        24

    .. seealso::

     - :func:`ssl_with_bad_version`
     - :func:`ssl_with_bad_defaults`
     - https://heartbleed.com/
     - https://en.wikipedia.org/wiki/POODLE
     - https://security.openstack.org/guidelines/dg_move-data-securely.html

    .. versionadded:: 0.9.0

    .. versionchanged:: 1.7.3
        CWE information added

    """
    if context.call_function_name_qual == "ssl.wrap_socket":
        if context.check_call_arg_value("ssl_version") is None:
            # check_call_arg_value() returns False if the argument is found
            # but does not match the supplied value (or the default None).
            # It returns None if the arg_name passed doesn't exist. This
            # tests for that (ssl_version is not specified).
            return bandit.Issue(
                severity=bandit.LOW,
                confidence=bandit.MEDIUM,
                cwe=issue.Cwe.BROKEN_CRYPTO,
                text="ssl.wrap_socket call with no SSL/TLS protocol version "
                "specified, the default SSLv23 could be insecure, "
                "possible security issue.",
                lineno=context.get_lineno_for_call_arg("ssl_version"),
            )
