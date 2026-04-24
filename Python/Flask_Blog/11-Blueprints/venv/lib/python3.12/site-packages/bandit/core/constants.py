#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
# default plugin name pattern
plugin_name_pattern = "*.py"

RANKING = ["UNDEFINED", "LOW", "MEDIUM", "HIGH"]
RANKING_VALUES = {"UNDEFINED": 1, "LOW": 3, "MEDIUM": 5, "HIGH": 10}
CRITERIA = [("SEVERITY", "UNDEFINED"), ("CONFIDENCE", "UNDEFINED")]

# add each ranking to globals, to allow direct access in module name space
for rank in RANKING:
    globals()[rank] = rank

CONFIDENCE_DEFAULT = "UNDEFINED"

# A list of values Python considers to be False.
# These can be useful in tests to check if a value is True or False.
# We don't handle the case of user-defined classes being false.
# These are only useful when we have a constant in code. If we
# have a variable we cannot determine if False.
# See https://docs.python.org/3/library/stdtypes.html#truth-value-testing
FALSE_VALUES = [None, False, "False", 0, 0.0, 0j, "", (), [], {}]

# override with "log_format" option in config file
log_format_string = "[%(module)s]\t%(levelname)s\t%(message)s"

# Directories to exclude by default
EXCLUDE = (
    ".svn",
    "CVS",
    ".bzr",
    ".hg",
    ".git",
    "__pycache__",
    ".tox",
    ".eggs",
    "*.egg",
)
