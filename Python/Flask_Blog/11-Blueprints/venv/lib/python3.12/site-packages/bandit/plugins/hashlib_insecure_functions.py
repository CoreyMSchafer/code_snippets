#
# SPDX-License-Identifier: Apache-2.0
r"""
======================================================================
B324: Test use of insecure md4, md5, or sha1 hash functions in hashlib
======================================================================

This plugin checks for the usage of the insecure MD4, MD5, or SHA1 hash
functions in ``hashlib`` and ``crypt``. The ``hashlib.new`` function provides
the ability to construct a new hashing object using the named algorithm. This
can be used to create insecure hash functions like MD4 and MD5 if they are
passed as algorithm names to this function.

This check does additional checking for usage of keyword usedforsecurity on all
function variations of hashlib.

Similar to ``hashlib``, this plugin also checks for usage of one of the
``crypt`` module's weak hashes. ``crypt`` also permits MD5 among other weak
hash variants.

:Example:

.. code-block:: none

    >> Issue: [B324:hashlib] Use of weak MD4, MD5, or SHA1 hash for
       security. Consider usedforsecurity=False
       Severity: High   Confidence: High
       CWE: CWE-327 (https://cwe.mitre.org/data/definitions/327.html)
       Location: examples/hashlib_new_insecure_functions.py:3:0
       More Info: https://bandit.readthedocs.io/en/latest/plugins/b324_hashlib.html
    2
    3   hashlib.new('md5')
    4

.. seealso::

 - https://cwe.mitre.org/data/definitions/327.html

.. versionadded:: 1.5.0

.. versionchanged:: 1.7.3
    CWE information added

.. versionchanged:: 1.7.6
    Added check for the crypt module weak hashes

"""  # noqa: E501
import bandit
from bandit.core import issue
from bandit.core import test_properties as test

WEAK_HASHES = ("md4", "md5", "sha", "sha1")
WEAK_CRYPT_HASHES = ("METHOD_CRYPT", "METHOD_MD5", "METHOD_BLOWFISH")


def _hashlib_func(context, func):
    keywords = context.call_keywords

    if func in WEAK_HASHES:
        if keywords.get("usedforsecurity", "True") == "True":
            return bandit.Issue(
                severity=bandit.HIGH,
                confidence=bandit.HIGH,
                cwe=issue.Cwe.BROKEN_CRYPTO,
                text=f"Use of weak {func.upper()} hash for security. "
                "Consider usedforsecurity=False",
                lineno=context.node.lineno,
            )
    elif func == "new":
        args = context.call_args
        name = args[0] if args else keywords.get("name", None)
        if isinstance(name, str) and name.lower() in WEAK_HASHES:
            if keywords.get("usedforsecurity", "True") == "True":
                return bandit.Issue(
                    severity=bandit.HIGH,
                    confidence=bandit.HIGH,
                    cwe=issue.Cwe.BROKEN_CRYPTO,
                    text=f"Use of weak {name.upper()} hash for "
                    "security. Consider usedforsecurity=False",
                    lineno=context.node.lineno,
                )


def _crypt_crypt(context, func):
    args = context.call_args
    keywords = context.call_keywords

    if func == "crypt":
        name = args[1] if len(args) > 1 else keywords.get("salt", None)
        if isinstance(name, str) and name in WEAK_CRYPT_HASHES:
            return bandit.Issue(
                severity=bandit.MEDIUM,
                confidence=bandit.HIGH,
                cwe=issue.Cwe.BROKEN_CRYPTO,
                text=f"Use of insecure crypt.{name.upper()} hash function.",
                lineno=context.node.lineno,
            )
    elif func == "mksalt":
        name = args[0] if args else keywords.get("method", None)
        if isinstance(name, str) and name in WEAK_CRYPT_HASHES:
            return bandit.Issue(
                severity=bandit.MEDIUM,
                confidence=bandit.HIGH,
                cwe=issue.Cwe.BROKEN_CRYPTO,
                text=f"Use of insecure crypt.{name.upper()} hash function.",
                lineno=context.node.lineno,
            )


@test.test_id("B324")
@test.checks("Call")
def hashlib(context):
    if isinstance(context.call_function_name_qual, str):
        qualname_list = context.call_function_name_qual.split(".")
        func = qualname_list[-1]

        if "hashlib" in qualname_list:
            return _hashlib_func(context, func)

        elif "crypt" in qualname_list and func in ("crypt", "mksalt"):
            return _crypt_crypt(context, func)
