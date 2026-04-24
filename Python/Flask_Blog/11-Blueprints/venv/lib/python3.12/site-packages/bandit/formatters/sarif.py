# Copyright (c) Microsoft.  All Rights Reserved.
#
# SPDX-License-Identifier: Apache-2.0
#
# Note: this code mostly incorporated from
# https://github.com/microsoft/bandit-sarif-formatter
#
r"""
===============
SARIF formatter
===============

This formatter outputs the issues in SARIF formatted JSON.

:Example:

.. code-block:: javascript

    {
      "runs": [
        {
          "tool": {
            "driver": {
              "name": "Bandit",
              "organization": "PyCQA",
              "rules": [
                {
                  "id": "B101",
                  "name": "assert_used",
                  "properties": {
                    "tags": [
                      "security",
                      "external/cwe/cwe-703"
                    ],
                    "precision": "high"
                  },
                  "helpUri": "https://bandit.readthedocs.io/en/1.7.8/plugins/b101_assert_used.html"
                }
              ],
              "version": "1.7.8",
              "semanticVersion": "1.7.8"
            }
          },
          "invocations": [
            {
              "executionSuccessful": true,
              "endTimeUtc": "2024-03-05T03:28:48Z"
            }
          ],
          "properties": {
            "metrics": {
              "_totals": {
                "loc": 1,
                "nosec": 0,
                "skipped_tests": 0,
                "SEVERITY.UNDEFINED": 0,
                "CONFIDENCE.UNDEFINED": 0,
                "SEVERITY.LOW": 1,
                "CONFIDENCE.LOW": 0,
                "SEVERITY.MEDIUM": 0,
                "CONFIDENCE.MEDIUM": 0,
                "SEVERITY.HIGH": 0,
                "CONFIDENCE.HIGH": 1
              },
              "./examples/assert.py": {
                "loc": 1,
                "nosec": 0,
                "skipped_tests": 0,
                "SEVERITY.UNDEFINED": 0,
                "SEVERITY.LOW": 1,
                "SEVERITY.MEDIUM": 0,
                "SEVERITY.HIGH": 0,
                "CONFIDENCE.UNDEFINED": 0,
                "CONFIDENCE.LOW": 0,
                "CONFIDENCE.MEDIUM": 0,
                "CONFIDENCE.HIGH": 1
              }
            }
          },
          "results": [
            {
              "message": {
                "text": "Use of assert detected. The enclosed code will be removed when compiling to optimised byte code."
              },
              "level": "note",
              "locations": [
                {
                  "physicalLocation": {
                    "region": {
                      "snippet": {
                        "text": "assert True\n"
                      },
                      "endColumn": 11,
                      "endLine": 1,
                      "startColumn": 0,
                      "startLine": 1
                    },
                    "artifactLocation": {
                      "uri": "examples/assert.py"
                    },
                    "contextRegion": {
                      "snippet": {
                        "text": "assert True\n"
                      },
                      "endLine": 1,
                      "startLine": 1
                    }
                  }
                }
              ],
              "properties": {
                "issue_confidence": "HIGH",
                "issue_severity": "LOW"
              },
              "ruleId": "B101",
              "ruleIndex": 0
            }
          ]
        }
      ],
      "version": "2.1.0",
      "$schema": "https://json.schemastore.org/sarif-2.1.0.json"
    }

.. versionadded:: 1.7.8

"""  # noqa: E501
import datetime
import logging
import pathlib
import sys
import urllib.parse as urlparse

import sarif_om as om
from jschema_to_python.to_json import to_json

import bandit
from bandit.core import docs_utils

LOG = logging.getLogger(__name__)
SCHEMA_URI = "https://json.schemastore.org/sarif-2.1.0.json"
SCHEMA_VER = "2.1.0"
TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def report(manager, fileobj, sev_level, conf_level, lines=-1):
    """Prints issues in SARIF format

    :param manager: the bandit manager object
    :param fileobj: The output file object, which may be sys.stdout
    :param sev_level: Filtering severity level
    :param conf_level: Filtering confidence level
    :param lines: Number of lines to report, -1 for all
    """

    log = om.SarifLog(
        schema_uri=SCHEMA_URI,
        version=SCHEMA_VER,
        runs=[
            om.Run(
                tool=om.Tool(
                    driver=om.ToolComponent(
                        name="Bandit",
                        organization=bandit.__author__,
                        semantic_version=bandit.__version__,
                        version=bandit.__version__,
                    )
                ),
                invocations=[
                    om.Invocation(
                        end_time_utc=datetime.datetime.now(
                            datetime.timezone.utc
                        ).strftime(TS_FORMAT),
                        execution_successful=True,
                    )
                ],
                properties={"metrics": manager.metrics.data},
            )
        ],
    )

    run = log.runs[0]
    invocation = run.invocations[0]

    skips = manager.get_skipped()
    add_skipped_file_notifications(skips, invocation)

    issues = manager.get_issue_list(sev_level=sev_level, conf_level=conf_level)

    add_results(issues, run)

    serializedLog = to_json(log)

    with fileobj:
        fileobj.write(serializedLog)

    if fileobj.name != sys.stdout.name:
        LOG.info("SARIF output written to file: %s", fileobj.name)


def add_skipped_file_notifications(skips, invocation):
    if skips is None or len(skips) == 0:
        return

    if invocation.tool_configuration_notifications is None:
        invocation.tool_configuration_notifications = []

    for skip in skips:
        (file_name, reason) = skip

        notification = om.Notification(
            level="error",
            message=om.Message(text=reason),
            locations=[
                om.Location(
                    physical_location=om.PhysicalLocation(
                        artifact_location=om.ArtifactLocation(
                            uri=to_uri(file_name)
                        )
                    )
                )
            ],
        )

        invocation.tool_configuration_notifications.append(notification)


def add_results(issues, run):
    if run.results is None:
        run.results = []

    rules = {}
    rule_indices = {}
    for issue in issues:
        result = create_result(issue, rules, rule_indices)
        run.results.append(result)

    if len(rules) > 0:
        run.tool.driver.rules = list(rules.values())


def create_result(issue, rules, rule_indices):
    issue_dict = issue.as_dict()

    rule, rule_index = create_or_find_rule(issue_dict, rules, rule_indices)

    physical_location = om.PhysicalLocation(
        artifact_location=om.ArtifactLocation(
            uri=to_uri(issue_dict["filename"])
        )
    )

    add_region_and_context_region(
        physical_location,
        issue_dict["line_range"],
        issue_dict["col_offset"],
        issue_dict["end_col_offset"],
        issue_dict["code"],
    )

    return om.Result(
        rule_id=rule.id,
        rule_index=rule_index,
        message=om.Message(text=issue_dict["issue_text"]),
        level=level_from_severity(issue_dict["issue_severity"]),
        locations=[om.Location(physical_location=physical_location)],
        properties={
            "issue_confidence": issue_dict["issue_confidence"],
            "issue_severity": issue_dict["issue_severity"],
        },
    )


def level_from_severity(severity):
    if severity == "HIGH":
        return "error"
    elif severity == "MEDIUM":
        return "warning"
    elif severity == "LOW":
        return "note"
    else:
        return "warning"


def add_region_and_context_region(
    physical_location, line_range, col_offset, end_col_offset, code
):
    if code:
        first_line_number, snippet_lines = parse_code(code)
        snippet_line = snippet_lines[line_range[0] - first_line_number]
        snippet = om.ArtifactContent(text=snippet_line)
    else:
        snippet = None

    physical_location.region = om.Region(
        start_line=line_range[0],
        end_line=line_range[1] if len(line_range) > 1 else line_range[0],
        start_column=col_offset + 1,
        end_column=end_col_offset + 1,
        snippet=snippet,
    )

    if code:
        physical_location.context_region = om.Region(
            start_line=first_line_number,
            end_line=first_line_number + len(snippet_lines) - 1,
            snippet=om.ArtifactContent(text="".join(snippet_lines)),
        )


def parse_code(code):
    code_lines = code.split("\n")

    # The last line from the split has nothing in it; it's an artifact of the
    # last "real" line ending in a newline. Unless, of course, it doesn't:
    last_line = code_lines[len(code_lines) - 1]

    last_real_line_ends_in_newline = False
    if len(last_line) == 0:
        code_lines.pop()
        last_real_line_ends_in_newline = True

    snippet_lines = []
    first_line_number = 0
    first = True
    for code_line in code_lines:
        number_and_snippet_line = code_line.split(" ", 1)
        if first:
            first_line_number = int(number_and_snippet_line[0])
            first = False

        snippet_line = number_and_snippet_line[1] + "\n"
        snippet_lines.append(snippet_line)

    if not last_real_line_ends_in_newline:
        last_line = snippet_lines[len(snippet_lines) - 1]
        snippet_lines[len(snippet_lines) - 1] = last_line[: len(last_line) - 1]

    return first_line_number, snippet_lines


def create_or_find_rule(issue_dict, rules, rule_indices):
    rule_id = issue_dict["test_id"]
    if rule_id in rules:
        return rules[rule_id], rule_indices[rule_id]

    rule = om.ReportingDescriptor(
        id=rule_id,
        name=issue_dict["test_name"],
        help_uri=docs_utils.get_url(rule_id),
        properties={
            "tags": [
                "security",
                f"external/cwe/cwe-{issue_dict['issue_cwe'].get('id')}",
            ],
            "precision": issue_dict["issue_confidence"].lower(),
        },
    )

    index = len(rules)
    rules[rule_id] = rule
    rule_indices[rule_id] = index
    return rule, index


def to_uri(file_path):
    pure_path = pathlib.PurePath(file_path)
    if pure_path.is_absolute():
        return pure_path.as_uri()
    else:
        # Replace backslashes with slashes.
        posix_path = pure_path.as_posix()
        # %-encode special characters.
        return urlparse.quote(posix_path)
