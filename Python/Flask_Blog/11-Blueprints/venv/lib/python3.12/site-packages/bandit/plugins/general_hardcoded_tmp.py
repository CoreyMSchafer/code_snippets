#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
r"""
===================================================
B108: Test for insecure usage of tmp file/directory
===================================================

Safely creating a temporary file or directory means following a number of rules
(see the references for more details). This plugin test looks for strings
starting with (configurable) commonly used temporary paths, for example:

 - /tmp
 - /var/tmp
 - /dev/shm

**Config Options:**

This test plugin takes a similarly named config block,
`hardcoded_tmp_directory`. The config block provides a Python list, `tmp_dirs`,
that lists string fragments indicating possible temporary file paths. Any
string starting with one of these fragments will report a MEDIUM confidence
issue.

.. code-block:: yaml

    hardcoded_tmp_directory:
        tmp_dirs: ['/tmp', '/var/tmp', '/dev/shm']


:Example:

.. code-block: none

    >> Issue: Probable insecure usage of temp file/directory.
       Severity: Medium   Confidence: Medium
       CWE: CWE-377 (https://cwe.mitre.org/data/definitions/377.html)
       Location: ./examples/hardcoded-tmp.py:1
    1 f = open('/tmp/abc', 'w')
    2 f.write('def')

.. seealso::

 - https://security.openstack.org/guidelines/dg_using-temporary-files-securely.html
 - https://cwe.mitre.org/data/definitions/377.html

.. versionadded:: 0.9.0

.. versionchanged:: 1.7.3
    CWE information added

"""  # noqa: E501
import bandit
from bandit.core import issue
from bandit.core import test_properties as test


def gen_config(name):
    if name == "hardcoded_tmp_directory":
        return {"tmp_dirs": ["/tmp", "/var/tmp", "/dev/shm"]}  # nosec: B108


@test.takes_config
@test.checks("Str")
@test.test_id("B108")
def hardcoded_tmp_directory(context, config):
    if config is not None and "tmp_dirs" in config:
        tmp_dirs = config["tmp_dirs"]
    else:
        tmp_dirs = ["/tmp", "/var/tmp", "/dev/shm"]  # nosec: B108

    if any(context.string_val.startswith(s) for s in tmp_dirs):
        return bandit.Issue(
            severity=bandit.MEDIUM,
            confidence=bandit.MEDIUM,
            cwe=issue.Cwe.INSECURE_TEMP_FILE,
            text="Probable insecure usage of temp file/directory.",
        )
