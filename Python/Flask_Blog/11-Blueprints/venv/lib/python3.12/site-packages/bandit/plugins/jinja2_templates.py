#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
r"""
==========================================
B701: Test for not auto escaping in jinja2
==========================================

Jinja2 is a Python HTML templating system. It is typically used to build web
applications, though appears in other places well, notably the Ansible
automation system. When configuring the Jinja2 environment, the option to use
autoescaping on input can be specified. When autoescaping is enabled, Jinja2
will filter input strings to escape any HTML content submitted via template
variables. Without escaping HTML input the application becomes vulnerable to
Cross Site Scripting (XSS) attacks.

Unfortunately, autoescaping is False by default. Thus this plugin test will
warn on omission of an autoescape setting, as well as an explicit setting of
false. A HIGH severity warning is generated in either of these scenarios.

:Example:

.. code-block:: none

    >> Issue: Using jinja2 templates with autoescape=False is dangerous and can
    lead to XSS. Use autoescape=True to mitigate XSS vulnerabilities.
       Severity: High   Confidence: High
       CWE: CWE-94 (https://cwe.mitre.org/data/definitions/94.html)
       Location: ./examples/jinja2_templating.py:11
    10  templateEnv = jinja2.Environment(autoescape=False,
        loader=templateLoader)
    11  Environment(loader=templateLoader,
    12              load=templateLoader,
    13              autoescape=False)
    14

    >> Issue: By default, jinja2 sets autoescape to False. Consider using
    autoescape=True or use the select_autoescape function to mitigate XSS
    vulnerabilities.
       Severity: High   Confidence: High
       CWE: CWE-94 (https://cwe.mitre.org/data/definitions/94.html)
       Location: ./examples/jinja2_templating.py:15
    14
    15  Environment(loader=templateLoader,
    16              load=templateLoader)
    17
    18  Environment(autoescape=select_autoescape(['html', 'htm', 'xml']),
    19              loader=templateLoader)


.. seealso::

 - `OWASP XSS <https://www.owasp.org/index.php/Cross-site_Scripting_(XSS)>`__
 - https://realpython.com/primer-on-jinja-templating/
 - https://jinja.palletsprojects.com/en/2.11.x/api/#autoescaping
 - https://security.openstack.org/guidelines/dg_cross-site-scripting-xss.html
 - https://cwe.mitre.org/data/definitions/94.html

.. versionadded:: 0.10.0

.. versionchanged:: 1.7.3
    CWE information added

"""
import ast

import bandit
from bandit.core import issue
from bandit.core import test_properties as test


@test.checks("Call")
@test.test_id("B701")
def jinja2_autoescape_false(context):
    # check type just to be safe
    if isinstance(context.call_function_name_qual, str):
        qualname_list = context.call_function_name_qual.split(".")
        func = qualname_list[-1]
        if "jinja2" in qualname_list and func == "Environment":
            for node in ast.walk(context.node):
                if isinstance(node, ast.keyword):
                    # definite autoescape = False
                    if getattr(node, "arg", None) == "autoescape" and (
                        getattr(node.value, "id", None) == "False"
                        or getattr(node.value, "value", None) is False
                    ):
                        return bandit.Issue(
                            severity=bandit.HIGH,
                            confidence=bandit.HIGH,
                            cwe=issue.Cwe.CODE_INJECTION,
                            text="Using jinja2 templates with autoescape="
                            "False is dangerous and can lead to XSS. "
                            "Use autoescape=True or use the "
                            "select_autoescape function to mitigate XSS "
                            "vulnerabilities.",
                        )
                    # found autoescape
                    if getattr(node, "arg", None) == "autoescape":
                        value = getattr(node, "value", None)
                        if (
                            getattr(value, "id", None) == "True"
                            or getattr(value, "value", None) is True
                        ):
                            return
                        # Check if select_autoescape function is used.
                        elif isinstance(value, ast.Call) and (
                            getattr(value.func, "attr", None)
                            == "select_autoescape"
                            or getattr(value.func, "id", None)
                            == "select_autoescape"
                        ):
                            return
                        else:
                            return bandit.Issue(
                                severity=bandit.HIGH,
                                confidence=bandit.MEDIUM,
                                cwe=issue.Cwe.CODE_INJECTION,
                                text="Using jinja2 templates with autoescape="
                                "False is dangerous and can lead to XSS. "
                                "Ensure autoescape=True or use the "
                                "select_autoescape function to mitigate "
                                "XSS vulnerabilities.",
                            )
            # We haven't found a keyword named autoescape, indicating default
            # behavior
            return bandit.Issue(
                severity=bandit.HIGH,
                confidence=bandit.HIGH,
                cwe=issue.Cwe.CODE_INJECTION,
                text="By default, jinja2 sets autoescape to False. Consider "
                "using autoescape=True or use the select_autoescape "
                "function to mitigate XSS vulnerabilities.",
            )
