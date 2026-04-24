#
# Copyright 2016 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
import ast

from bandit.core import issue


def report_issue(check, name):
    return issue.Issue(
        severity=check.get("level", "MEDIUM"),
        confidence="HIGH",
        cwe=check.get("cwe", issue.Cwe.NOTSET),
        text=check["message"].replace("{name}", name),
        ident=name,
        test_id=check.get("id", "LEGACY"),
    )


def blacklist(context, config):
    """Generic blacklist test, B001.

    This generic blacklist test will be called for any encountered node with
    defined blacklist data available. This data is loaded via plugins using
    the 'bandit.blacklists' entry point. Please see the documentation for more
    details. Each blacklist datum has a unique bandit ID that may be used for
    filtering purposes, or alternatively all blacklisting can be filtered using
    the id of this built in test, 'B001'.
    """
    blacklists = config
    node_type = context.node.__class__.__name__

    if node_type == "Call":
        func = context.node.func
        if isinstance(func, ast.Name) and func.id == "__import__":
            if len(context.node.args):
                if isinstance(
                    context.node.args[0], ast.Constant
                ) and isinstance(context.node.args[0].value, str):
                    name = context.node.args[0].value
                else:
                    # TODO(??): import through a variable, need symbol tab
                    name = "UNKNOWN"
            else:
                name = ""  # handle '__import__()'
        else:
            name = context.call_function_name_qual
            # In the case the Call is an importlib.import, treat the first
            # argument name as an actual import module name.
            # Will produce None if argument is not a literal or identifier
            if name in ["importlib.import_module", "importlib.__import__"]:
                if context.call_args_count > 0:
                    name = context.call_args[0]
                else:
                    name = context.call_keywords["name"]
        for check in blacklists[node_type]:
            for qn in check["qualnames"]:
                if name is not None and name == qn:
                    return report_issue(check, name)

    if node_type.startswith("Import"):
        prefix = ""
        if node_type == "ImportFrom":
            if context.node.module is not None:
                prefix = context.node.module + "."

        for check in blacklists[node_type]:
            for name in context.node.names:
                for qn in check["qualnames"]:
                    if (prefix + name.name).startswith(qn):
                        return report_issue(check, name.name)
