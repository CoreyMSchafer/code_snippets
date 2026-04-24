# Copyright (c) 2025 David Salvisberg
#
# SPDX-License-Identifier: Apache-2.0
r"""
============================================
B704: Potential XSS on markupsafe.Markup use
============================================

``markupsafe.Markup`` does not perform any escaping, so passing dynamic
content, like f-strings, variables or interpolated strings will potentially
lead to XSS vulnerabilities, especially if that data was submitted by users.

Instead you should interpolate the resulting ``markupsafe.Markup`` object,
which will perform escaping, or use ``markupsafe.escape``.


**Config Options:**

This plugin allows you to specify additional callable that should be treated
like ``markupsafe.Markup``. By default we recognize ``flask.Markup`` as
an alias, but there are other subclasses or similar classes in the wild
that you may wish to treat the same.

Additionally there is a whitelist for callable names, whose result may
be safely passed into ``markupsafe.Markup``. This is useful for escape
functions like e.g. ``bleach.clean`` which don't themselves return
``markupsafe.Markup``, so they need to be wrapped. Take care when using
this setting, since incorrect use may introduce false negatives.

These two options can be set in a shared configuration section
`markupsafe_xss`.


.. code-block:: yaml

    markupsafe_xss:
        # Recognize additional aliases
        extend_markup_names:
            - webhelpers.html.literal
            - my_package.Markup

        # Allow the output of these functions to pass into Markup
        allowed_calls:
            - bleach.clean
            - my_package.sanitize


:Example:

.. code-block:: none

    >> Issue: [B704:markupsafe_markup_xss] Potential XSS with
       ``markupsafe.Markup`` detected. Do not use ``Markup``
       on untrusted data.
       Severity: Medium   Confidence: High
       CWE: CWE-79 (https://cwe.mitre.org/data/definitions/79.html)
       Location: ./examples/markupsafe_markup_xss.py:5:0
    4       content = "<script>alert('Hello, world!')</script>"
    5       Markup(f"unsafe {content}")
    6       flask.Markup("unsafe {}".format(content))

.. seealso::

 - https://pypi.org/project/MarkupSafe/
 - https://markupsafe.palletsprojects.com/en/stable/escaping/#markupsafe.Markup
 - https://cwe.mitre.org/data/definitions/79.html

.. versionadded:: 1.8.3

"""
import ast

import bandit
from bandit.core import issue
from bandit.core import test_properties as test
from bandit.core.utils import get_call_name


def gen_config(name):
    if name == "markupsafe_xss":
        return {
            "extend_markup_names": [],
            "allowed_calls": [],
        }


@test.takes_config("markupsafe_xss")
@test.checks("Call")
@test.test_id("B704")
def markupsafe_markup_xss(context, config):

    qualname = context.call_function_name_qual
    if qualname not in ("markupsafe.Markup", "flask.Markup"):
        if qualname not in config.get("extend_markup_names", []):
            # not a Markup call
            return None

    args = context.node.args
    if not args or isinstance(args[0], ast.Constant):
        # both no arguments and a constant are fine
        return None

    allowed_calls = config.get("allowed_calls", [])
    if (
        allowed_calls
        and isinstance(args[0], ast.Call)
        and get_call_name(args[0], context.import_aliases) in allowed_calls
    ):
        # the argument contains a whitelisted call
        return None

    return bandit.Issue(
        severity=bandit.MEDIUM,
        confidence=bandit.HIGH,
        cwe=issue.Cwe.XSS,
        text=f"Potential XSS with ``{qualname}`` detected. Do "
        f"not use ``{context.call_function_name}`` on untrusted data.",
    )
