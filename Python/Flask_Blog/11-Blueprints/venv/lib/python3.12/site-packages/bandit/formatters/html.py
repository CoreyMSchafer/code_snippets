# Copyright (c) 2015 Rackspace, Inc.
# Copyright (c) 2015 Hewlett Packard Enterprise
#
# SPDX-License-Identifier: Apache-2.0
r"""
==============
HTML formatter
==============

This formatter outputs the issues as HTML.

:Example:

.. code-block:: html

    <!DOCTYPE html>
    <html>
    <head>

    <meta charset="UTF-8">

    <title>
        Bandit Report
    </title>

    <style>

    html * {
        font-family: "Arial", sans-serif;
    }

    pre {
        font-family: "Monaco", monospace;
    }

    .bordered-box {
        border: 1px solid black;
        padding-top:.5em;
        padding-bottom:.5em;
        padding-left:1em;
    }

    .metrics-box {
        font-size: 1.1em;
        line-height: 130%;
    }

    .metrics-title {
        font-size: 1.5em;
        font-weight: 500;
        margin-bottom: .25em;
    }

    .issue-description {
        font-size: 1.3em;
        font-weight: 500;
    }

    .candidate-issues {
        margin-left: 2em;
        border-left: solid 1px; LightGray;
        padding-left: 5%;
        margin-top: .2em;
        margin-bottom: .2em;
    }

    .issue-block {
        border: 1px solid LightGray;
        padding-left: .5em;
        padding-top: .5em;
        padding-bottom: .5em;
        margin-bottom: .5em;
    }

    .issue-sev-high {
        background-color: Pink;
    }

    .issue-sev-medium {
        background-color: NavajoWhite;
    }

    .issue-sev-low {
        background-color: LightCyan;
    }

    </style>
    </head>

    <body>

    <div id="metrics">
        <div class="metrics-box bordered-box">
            <div class="metrics-title">
                Metrics:<br>
            </div>
            Total lines of code: <span id="loc">9</span><br>
            Total lines skipped (#nosec): <span id="nosec">0</span>
        </div>
    </div>




    <br>
    <div id="results">

    <div id="issue-0">
    <div class="issue-block issue-sev-medium">
        <b>yaml_load: </b> Use of unsafe yaml load. Allows
        instantiation of arbitrary objects. Consider yaml.safe_load().<br>
        <b>Test ID:</b> B506<br>
        <b>Severity: </b>MEDIUM<br>
        <b>Confidence: </b>HIGH<br>
        <b>CWE: </b>CWE-20 (https://cwe.mitre.org/data/definitions/20.html)<br>
        <b>File: </b><a href="examples/yaml_load.py"
        target="_blank">examples/yaml_load.py</a> <br>
        <b>More info: </b><a href="https://bandit.readthedocs.io/en/latest/
        plugins/yaml_load.html" target="_blank">
        https://bandit.readthedocs.io/en/latest/plugins/yaml_load.html</a>
        <br>

    <div class="code">
    <pre>
    5       ystr = yaml.dump({'a' : 1, 'b' : 2, 'c' : 3})
    6       y = yaml.load(ystr)
    7       yaml.dump(y)
    </pre>
    </div>


    </div>
    </div>

    </div>

    </body>
    </html>

.. versionadded:: 0.14.0

.. versionchanged:: 1.5.0
    New field `more_info` added to output

.. versionchanged:: 1.7.3
    New field `CWE` added to output

"""
import logging
import sys
from html import escape as html_escape

from bandit.core import docs_utils
from bandit.core import test_properties
from bandit.formatters import utils

LOG = logging.getLogger(__name__)


@test_properties.accepts_baseline
def report(manager, fileobj, sev_level, conf_level, lines=-1):
    """Writes issues to 'fileobj' in HTML format

    :param manager: the bandit manager object
    :param fileobj: The output file object, which may be sys.stdout
    :param sev_level: Filtering severity level
    :param conf_level: Filtering confidence level
    :param lines: Number of lines to report, -1 for all
    """

    header_block = """
<!DOCTYPE html>
<html>
<head>

<meta charset="UTF-8">

<title>
    Bandit Report
</title>

<style>

html * {
    font-family: "Arial", sans-serif;
}

pre {
    font-family: "Monaco", monospace;
}

.bordered-box {
    border: 1px solid black;
    padding-top:.5em;
    padding-bottom:.5em;
    padding-left:1em;
}

.metrics-box {
    font-size: 1.1em;
    line-height: 130%;
}

.metrics-title {
    font-size: 1.5em;
    font-weight: 500;
    margin-bottom: .25em;
}

.issue-description {
    font-size: 1.3em;
    font-weight: 500;
}

.candidate-issues {
    margin-left: 2em;
    border-left: solid 1px; LightGray;
    padding-left: 5%;
    margin-top: .2em;
    margin-bottom: .2em;
}

.issue-block {
    border: 1px solid LightGray;
    padding-left: .5em;
    padding-top: .5em;
    padding-bottom: .5em;
    margin-bottom: .5em;
}

.issue-sev-high {
    background-color: Pink;
}

.issue-sev-medium {
    background-color: NavajoWhite;
}

.issue-sev-low {
    background-color: LightCyan;
}

</style>
</head>
"""

    report_block = """
<body>
{metrics}
{skipped}

<br>
<div id="results">
    {results}
</div>

</body>
</html>
"""

    issue_block = """
<div id="issue-{issue_no}">
<div class="issue-block {issue_class}">
    <b>{test_name}: </b> {test_text}<br>
    <b>Test ID:</b> {test_id}<br>
    <b>Severity: </b>{severity}<br>
    <b>Confidence: </b>{confidence}<br>
    <b>CWE: </b><a href="{cwe_link}" target="_blank">CWE-{cwe.id}</a><br>
    <b>File: </b><a href="{path}" target="_blank">{path}</a><br>
    <b>Line number: </b>{line_number}<br>
    <b>More info: </b><a href="{url}" target="_blank">{url}</a><br>
{code}
{candidates}
</div>
</div>
"""

    code_block = """
<div class="code">
<pre>
{code}
</pre>
</div>
"""

    candidate_block = """
<div class="candidates">
<br>
<b>Candidates: </b>
{candidate_list}
</div>
"""

    candidate_issue = """
<div class="candidate">
<div class="candidate-issues">
<pre>{code}</pre>
</div>
</div>
"""

    skipped_block = """
<br>
<div id="skipped">
<div class="bordered-box">
<b>Skipped files:</b><br><br>
{files_list}
</div>
</div>
"""

    metrics_block = """
<div id="metrics">
    <div class="metrics-box bordered-box">
        <div class="metrics-title">
            Metrics:<br>
        </div>
        Total lines of code: <span id="loc">{loc}</span><br>
        Total lines skipped (#nosec): <span id="nosec">{nosec}</span>
    </div>
</div>

"""

    issues = manager.get_issue_list(sev_level=sev_level, conf_level=conf_level)

    baseline = not isinstance(issues, list)

    # build the skipped string to insert in the report
    skipped_str = "".join(
        f"{fname} <b>reason:</b> {reason}<br>"
        for fname, reason in manager.get_skipped()
    )
    if skipped_str:
        skipped_text = skipped_block.format(files_list=skipped_str)
    else:
        skipped_text = ""

    # build the results string to insert in the report
    results_str = ""
    for index, issue in enumerate(issues):
        if not baseline or len(issues[issue]) == 1:
            candidates = ""
            safe_code = html_escape(
                issue.get_code(lines, True).strip("\n").lstrip(" ")
            )
            code = code_block.format(code=safe_code)
        else:
            candidates_str = ""
            code = ""
            for candidate in issues[issue]:
                candidate_code = html_escape(
                    candidate.get_code(lines, True).strip("\n").lstrip(" ")
                )
                candidates_str += candidate_issue.format(code=candidate_code)

            candidates = candidate_block.format(candidate_list=candidates_str)

        url = docs_utils.get_url(issue.test_id)
        results_str += issue_block.format(
            issue_no=index,
            issue_class=f"issue-sev-{issue.severity.lower()}",
            test_name=issue.test,
            test_id=issue.test_id,
            test_text=issue.text,
            severity=issue.severity,
            confidence=issue.confidence,
            cwe=issue.cwe,
            cwe_link=issue.cwe.link(),
            path=issue.fname,
            code=code,
            candidates=candidates,
            url=url,
            line_number=issue.lineno,
        )

    # build the metrics string to insert in the report
    metrics_summary = metrics_block.format(
        loc=manager.metrics.data["_totals"]["loc"],
        nosec=manager.metrics.data["_totals"]["nosec"],
    )

    # build the report and output it
    report_contents = report_block.format(
        metrics=metrics_summary, skipped=skipped_text, results=results_str
    )

    with fileobj:
        wrapped_file = utils.wrap_file_object(fileobj)
        wrapped_file.write(header_block)
        wrapped_file.write(report_contents)

    if fileobj.name != sys.stdout.name:
        LOG.info("HTML output written to file: %s", fileobj.name)
