#
# SPDX-License-Identifier: Apache-2.0
#
r"""
=================================
B202: Test for tarfile.extractall
=================================

This plugin will look for usage of ``tarfile.extractall()``

Severity are set as follows:

* ``tarfile.extractall(members=function(tarfile))`` - LOW
* ``tarfile.extractall(members=?)`` - member is not a function - MEDIUM
* ``tarfile.extractall()`` - members from the archive is trusted - HIGH

Use ``tarfile.extractall(members=function_name)`` and define a function
that will inspect each member. Discard files that contain a directory
traversal sequences such as ``../`` or ``\..`` along with all special filetypes
unless you explicitly need them.

:Example:

.. code-block:: none

    >> Issue: [B202:tarfile_unsafe_members] tarfile.extractall used without
    any validation. You should check members and discard dangerous ones
    Severity: High   Confidence: High
    CWE: CWE-22 (https://cwe.mitre.org/data/definitions/22.html)
    Location: examples/tarfile_extractall.py:8
    More Info:
    https://bandit.readthedocs.io/en/latest/plugins/b202_tarfile_unsafe_members.html
    7	    tar = tarfile.open(filename)
    8	    tar.extractall(path=tempfile.mkdtemp())
    9	    tar.close()


.. seealso::

 - https://docs.python.org/3/library/tarfile.html#tarfile.TarFile.extractall
 - https://docs.python.org/3/library/tarfile.html#tarfile.TarInfo

.. versionadded:: 1.7.5

.. versionchanged:: 1.7.8
    Added check for filter parameter

"""
import ast

import bandit
from bandit.core import issue
from bandit.core import test_properties as test


def exec_issue(level, members=""):
    if level == bandit.LOW:
        return bandit.Issue(
            severity=bandit.LOW,
            confidence=bandit.LOW,
            cwe=issue.Cwe.PATH_TRAVERSAL,
            text="Usage of tarfile.extractall(members=function(tarfile)). "
            "Make sure your function properly discards dangerous members "
            "{members}).".format(members=members),
        )
    elif level == bandit.MEDIUM:
        return bandit.Issue(
            severity=bandit.MEDIUM,
            confidence=bandit.MEDIUM,
            cwe=issue.Cwe.PATH_TRAVERSAL,
            text="Found tarfile.extractall(members=?) but couldn't "
            "identify the type of members. "
            "Check if the members were properly validated "
            "{members}).".format(members=members),
        )
    else:
        return bandit.Issue(
            severity=bandit.HIGH,
            confidence=bandit.HIGH,
            cwe=issue.Cwe.PATH_TRAVERSAL,
            text="tarfile.extractall used without any validation. "
            "Please check and discard dangerous members.",
        )


def get_members_value(context):
    for keyword in context.node.keywords:
        if keyword.arg == "members":
            arg = keyword.value
            if isinstance(arg, ast.Call):
                return {"Function": arg.func.id}
            else:
                value = arg.id if isinstance(arg, ast.Name) else arg
                return {"Other": value}


def is_filter_data(context):
    for keyword in context.node.keywords:
        if keyword.arg == "filter":
            arg = keyword.value
            return isinstance(arg, ast.Constant) and arg.value == "data"


@test.test_id("B202")
@test.checks("Call")
def tarfile_unsafe_members(context):
    if all(
        [
            context.is_module_imported_exact("tarfile"),
            "extractall" in context.call_function_name,
        ]
    ):
        if "filter" in context.call_keywords and is_filter_data(context):
            return None
        if "members" in context.call_keywords:
            members = get_members_value(context)
            if "Function" in members:
                return exec_issue(bandit.LOW, members)
            else:
                return exec_issue(bandit.MEDIUM, members)
        return exec_issue(bandit.HIGH)
