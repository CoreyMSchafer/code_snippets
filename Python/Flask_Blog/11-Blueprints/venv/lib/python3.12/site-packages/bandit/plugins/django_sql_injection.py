#
# Copyright (C) 2018 [Victor Torre](https://github.com/ehooo)
#
# SPDX-License-Identifier: Apache-2.0
import ast

import bandit
from bandit.core import issue
from bandit.core import test_properties as test


def keywords2dict(keywords):
    kwargs = {}
    for node in keywords:
        if isinstance(node, ast.keyword):
            kwargs[node.arg] = node.value
    return kwargs


@test.checks("Call")
@test.test_id("B610")
def django_extra_used(context):
    """**B610: Potential SQL injection on extra function**

    :Example:

    .. code-block:: none

        >> Issue: [B610:django_extra_used] Use of extra potential SQL attack vector.
           Severity: Medium Confidence: Medium
           CWE: CWE-89 (https://cwe.mitre.org/data/definitions/89.html)
           Location: examples/django_sql_injection_extra.py:29:0
           More Info: https://bandit.readthedocs.io/en/latest/plugins/b610_django_extra_used.html
        28  tables_str = 'django_content_type" WHERE "auth_user"."username"="admin'
        29  User.objects.all().extra(tables=[tables_str]).distinct()

    .. seealso::

     - https://docs.djangoproject.com/en/dev/topics/security/\
#sql-injection-protection
     - https://cwe.mitre.org/data/definitions/89.html

    .. versionadded:: 1.5.0

    .. versionchanged:: 1.7.3
        CWE information added

    """  # noqa: E501
    description = "Use of extra potential SQL attack vector."
    if context.call_function_name == "extra":
        kwargs = keywords2dict(context.node.keywords)
        args = context.node.args
        if args:
            if len(args) >= 1:
                kwargs["select"] = args[0]
            if len(args) >= 2:
                kwargs["where"] = args[1]
            if len(args) >= 3:
                kwargs["params"] = args[2]
            if len(args) >= 4:
                kwargs["tables"] = args[3]
            if len(args) >= 5:
                kwargs["order_by"] = args[4]
            if len(args) >= 6:
                kwargs["select_params"] = args[5]
        insecure = False
        for key in ["where", "tables"]:
            if key in kwargs:
                if isinstance(kwargs[key], ast.List):
                    for val in kwargs[key].elts:
                        if not (
                            isinstance(val, ast.Constant)
                            and isinstance(val.value, str)
                        ):
                            insecure = True
                            break
                else:
                    insecure = True
                    break
        if not insecure and "select" in kwargs:
            if isinstance(kwargs["select"], ast.Dict):
                for k in kwargs["select"].keys:
                    if not (
                        isinstance(k, ast.Constant)
                        and isinstance(k.value, str)
                    ):
                        insecure = True
                        break
                if not insecure:
                    for v in kwargs["select"].values:
                        if not (
                            isinstance(v, ast.Constant)
                            and isinstance(v.value, str)
                        ):
                            insecure = True
                            break
            else:
                insecure = True

        if insecure:
            return bandit.Issue(
                severity=bandit.MEDIUM,
                confidence=bandit.MEDIUM,
                cwe=issue.Cwe.SQL_INJECTION,
                text=description,
            )


@test.checks("Call")
@test.test_id("B611")
def django_rawsql_used(context):
    """**B611: Potential SQL injection on RawSQL function**

    :Example:

    .. code-block:: none

        >> Issue: [B611:django_rawsql_used] Use of RawSQL potential SQL attack vector.
           Severity: Medium Confidence: Medium
           CWE: CWE-89 (https://cwe.mitre.org/data/definitions/89.html)
           Location: examples/django_sql_injection_raw.py:11:26
           More Info: https://bandit.readthedocs.io/en/latest/plugins/b611_django_rawsql_used.html
        10        ' WHERE "username"="admin" OR 1=%s --'
        11  User.objects.annotate(val=RawSQL(raw, [0]))

    .. seealso::

     - https://docs.djangoproject.com/en/dev/topics/security/\
#sql-injection-protection
     - https://cwe.mitre.org/data/definitions/89.html

    .. versionadded:: 1.5.0

    .. versionchanged:: 1.7.3
        CWE information added

    """  # noqa: E501
    description = "Use of RawSQL potential SQL attack vector."
    if context.is_module_imported_like("django.db.models"):
        if context.call_function_name == "RawSQL":
            if context.node.args:
                sql = context.node.args[0]
            else:
                kwargs = keywords2dict(context.node.keywords)
                sql = kwargs["sql"]

            if not (
                isinstance(sql, ast.Constant) and isinstance(sql.value, str)
            ):
                return bandit.Issue(
                    severity=bandit.MEDIUM,
                    confidence=bandit.MEDIUM,
                    cwe=issue.Cwe.SQL_INJECTION,
                    text=description,
                )
