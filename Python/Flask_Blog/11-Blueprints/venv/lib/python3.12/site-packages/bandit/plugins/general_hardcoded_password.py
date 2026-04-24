#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
import ast
import re

import bandit
from bandit.core import issue
from bandit.core import test_properties as test

RE_WORDS = "(pas+wo?r?d|pass(phrase)?|pwd|token|secrete?)"
RE_CANDIDATES = re.compile(
    "(^{0}$|_{0}_|^{0}_|_{0}$)".format(RE_WORDS), re.IGNORECASE
)


def _report(value, lineno=None):
    return bandit.Issue(
        severity=bandit.LOW,
        confidence=bandit.MEDIUM,
        cwe=issue.Cwe.HARD_CODED_PASSWORD,
        text=f"Possible hardcoded password: '{value}'",
        lineno=lineno,
    )


@test.checks("Str")
@test.test_id("B105")
def hardcoded_password_string(context):
    """**B105: Test for use of hard-coded password strings**

    The use of hard-coded passwords increases the possibility of password
    guessing tremendously. This plugin test looks for all string literals and
    checks the following conditions:

    - assigned to a variable that looks like a password
    - assigned to a dict key that looks like a password
    - assigned to a class attribute that looks like a password
    - used in a comparison with a variable that looks like a password

    Variables are considered to look like a password if they have match any one
    of:

    - "password"
    - "pass"
    - "passwd"
    - "pwd"
    - "secret"
    - "token"
    - "secrete"

    Note: this can be noisy and may generate false positives.

    **Config Options:**

    None

    :Example:

    .. code-block:: none

        >> Issue: Possible hardcoded password '(root)'
           Severity: Low   Confidence: Low
           CWE: CWE-259 (https://cwe.mitre.org/data/definitions/259.html)
           Location: ./examples/hardcoded-passwords.py:5
        4 def someFunction2(password):
        5     if password == "root":
        6         print("OK, logged in")

    .. seealso::

        - https://www.owasp.org/index.php/Use_of_hard-coded_password
        - https://cwe.mitre.org/data/definitions/259.html

    .. versionadded:: 0.9.0

    .. versionchanged:: 1.7.3
        CWE information added

    """
    node = context.node
    if isinstance(node._bandit_parent, ast.Assign):
        # looks for "candidate='some_string'"
        for targ in node._bandit_parent.targets:
            if isinstance(targ, ast.Name) and RE_CANDIDATES.search(targ.id):
                return _report(node.value)
            elif isinstance(targ, ast.Attribute) and RE_CANDIDATES.search(
                targ.attr
            ):
                return _report(node.value)

    elif (
        isinstance(node._bandit_parent, ast.Dict)
        and node in node._bandit_parent.keys
        and RE_CANDIDATES.search(node.value)
    ):
        # looks for "{'candidate': 'some_string'}"
        dict_node = node._bandit_parent
        pos = dict_node.keys.index(node)
        value_node = dict_node.values[pos]
        if isinstance(value_node, ast.Constant):
            return _report(value_node.value)

    elif isinstance(
        node._bandit_parent, ast.Subscript
    ) and RE_CANDIDATES.search(node.value):
        # Py39+: looks for "dict[candidate]='some_string'"
        # subscript -> index -> string
        assign = node._bandit_parent._bandit_parent
        if (
            isinstance(assign, ast.Assign)
            and isinstance(assign.value, ast.Constant)
            and isinstance(assign.value.value, str)
        ):
            return _report(assign.value.value)

    elif isinstance(node._bandit_parent, ast.Index) and RE_CANDIDATES.search(
        node.value
    ):
        # looks for "dict[candidate]='some_string'"
        # assign -> subscript -> index -> string
        assign = node._bandit_parent._bandit_parent._bandit_parent
        if (
            isinstance(assign, ast.Assign)
            and isinstance(assign.value, ast.Constant)
            and isinstance(assign.value.value, str)
        ):
            return _report(assign.value.value)

    elif isinstance(node._bandit_parent, ast.Compare):
        # looks for "candidate == 'some_string'"
        comp = node._bandit_parent
        if isinstance(comp.left, ast.Name):
            if RE_CANDIDATES.search(comp.left.id):
                if isinstance(
                    comp.comparators[0], ast.Constant
                ) and isinstance(comp.comparators[0].value, str):
                    return _report(comp.comparators[0].value)
        elif isinstance(comp.left, ast.Attribute):
            if RE_CANDIDATES.search(comp.left.attr):
                if isinstance(
                    comp.comparators[0], ast.Constant
                ) and isinstance(comp.comparators[0].value, str):
                    return _report(comp.comparators[0].value)


@test.checks("Call")
@test.test_id("B106")
def hardcoded_password_funcarg(context):
    """**B106: Test for use of hard-coded password function arguments**

    The use of hard-coded passwords increases the possibility of password
    guessing tremendously. This plugin test looks for all function calls being
    passed a keyword argument that is a string literal. It checks that the
    assigned local variable does not look like a password.

    Variables are considered to look like a password if they have match any one
    of:

    - "password"
    - "pass"
    - "passwd"
    - "pwd"
    - "secret"
    - "token"
    - "secrete"

    Note: this can be noisy and may generate false positives.

    **Config Options:**

    None

    :Example:

    .. code-block:: none

        >> Issue: [B106:hardcoded_password_funcarg] Possible hardcoded
        password: 'blerg'
           Severity: Low   Confidence: Medium
           CWE: CWE-259 (https://cwe.mitre.org/data/definitions/259.html)
           Location: ./examples/hardcoded-passwords.py:16
        15
        16    doLogin(password="blerg")

    .. seealso::

        - https://www.owasp.org/index.php/Use_of_hard-coded_password
        - https://cwe.mitre.org/data/definitions/259.html

    .. versionadded:: 0.9.0

    .. versionchanged:: 1.7.3
        CWE information added

    """
    # looks for "function(candidate='some_string')"
    for kw in context.node.keywords:
        if (
            isinstance(kw.value, ast.Constant)
            and isinstance(kw.value.value, str)
            and RE_CANDIDATES.search(kw.arg)
        ):
            return _report(kw.value.value, lineno=kw.value.lineno)


@test.checks("FunctionDef")
@test.test_id("B107")
def hardcoded_password_default(context):
    """**B107: Test for use of hard-coded password argument defaults**

    The use of hard-coded passwords increases the possibility of password
    guessing tremendously. This plugin test looks for all function definitions
    that specify a default string literal for some argument. It checks that
    the argument does not look like a password.

    Variables are considered to look like a password if they have match any one
    of:

    - "password"
    - "pass"
    - "passwd"
    - "pwd"
    - "secret"
    - "token"
    - "secrete"

    Note: this can be noisy and may generate false positives.  We do not
    report on None values which can be legitimately used as a default value,
    when initializing a function or class.

    **Config Options:**

    None

    :Example:

    .. code-block:: none

        >> Issue: [B107:hardcoded_password_default] Possible hardcoded
        password: 'Admin'
           Severity: Low   Confidence: Medium
           CWE: CWE-259 (https://cwe.mitre.org/data/definitions/259.html)
           Location: ./examples/hardcoded-passwords.py:1

        1    def someFunction(user, password="Admin"):
        2      print("Hi " + user)

    .. seealso::

        - https://www.owasp.org/index.php/Use_of_hard-coded_password
        - https://cwe.mitre.org/data/definitions/259.html

    .. versionadded:: 0.9.0

    .. versionchanged:: 1.7.3
        CWE information added

    """
    # looks for "def function(candidate='some_string')"

    # this pads the list of default values with "None" if nothing is given
    defs = [None] * (
        len(context.node.args.args) - len(context.node.args.defaults)
    )
    defs.extend(context.node.args.defaults)

    # go through all (param, value)s and look for candidates
    for key, val in zip(context.node.args.args, defs):
        if isinstance(key, (ast.Name, ast.arg)):
            # Skip if the default value is None
            if val is None or (
                isinstance(val, ast.Constant) and val.value is None
            ):
                continue
            if (
                isinstance(val, ast.Constant)
                and isinstance(val.value, str)
                and RE_CANDIDATES.search(key.arg)
            ):
                return _report(val.value)
