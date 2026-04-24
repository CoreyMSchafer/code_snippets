#
# SPDX-License-Identifier: Apache-2.0
r"""
==============
JSON formatter
==============

This formatter outputs the issues in JSON.

:Example:

.. code-block:: javascript

    {
      "errors": [],
      "generated_at": "2015-12-16T22:27:34Z",
      "metrics": {
        "_totals": {
          "CONFIDENCE.HIGH": 1,
          "CONFIDENCE.LOW": 0,
          "CONFIDENCE.MEDIUM": 0,
          "CONFIDENCE.UNDEFINED": 0,
          "SEVERITY.HIGH": 0,
          "SEVERITY.LOW": 0,
          "SEVERITY.MEDIUM": 1,
          "SEVERITY.UNDEFINED": 0,
          "loc": 5,
          "nosec": 0
        },
        "examples/yaml_load.py": {
          "CONFIDENCE.HIGH": 1,
          "CONFIDENCE.LOW": 0,
          "CONFIDENCE.MEDIUM": 0,
          "CONFIDENCE.UNDEFINED": 0,
          "SEVERITY.HIGH": 0,
          "SEVERITY.LOW": 0,
          "SEVERITY.MEDIUM": 1,
          "SEVERITY.UNDEFINED": 0,
          "loc": 5,
          "nosec": 0
        }
      },
      "results": [
        {
          "code": "4     ystr = yaml.dump({'a' : 1, 'b' : 2, 'c' : 3})\n5
                         y = yaml.load(ystr)\n6     yaml.dump(y)\n",
          "filename": "examples/yaml_load.py",
          "issue_confidence": "HIGH",
          "issue_severity": "MEDIUM",
          "issue_cwe": {
            "id": 20,
            "link": "https://cwe.mitre.org/data/definitions/20.html"
          },
          "issue_text": "Use of unsafe yaml load. Allows instantiation of
                         arbitrary objects. Consider yaml.safe_load().\n",
          "line_number": 5,
          "line_range": [
            5
          ],
          "more_info": "https://bandit.readthedocs.io/en/latest/",
          "test_name": "blacklist_calls",
          "test_id": "B301"
        }
      ]
    }

.. versionadded:: 0.10.0

.. versionchanged:: 1.5.0
    New field `more_info` added to output

.. versionchanged:: 1.7.3
    New field `CWE` added to output

"""
# Necessary so we can import the standard library json module while continuing
# to name this file json.py. (Python 2 only)
import datetime
import json
import logging
import operator
import sys

from bandit.core import docs_utils
from bandit.core import test_properties

LOG = logging.getLogger(__name__)


@test_properties.accepts_baseline
def report(manager, fileobj, sev_level, conf_level, lines=-1):
    """''Prints issues in JSON format

    :param manager: the bandit manager object
    :param fileobj: The output file object, which may be sys.stdout
    :param sev_level: Filtering severity level
    :param conf_level: Filtering confidence level
    :param lines: Number of lines to report, -1 for all
    """

    machine_output = {"results": [], "errors": []}
    for fname, reason in manager.get_skipped():
        machine_output["errors"].append({"filename": fname, "reason": reason})

    results = manager.get_issue_list(
        sev_level=sev_level, conf_level=conf_level
    )

    baseline = not isinstance(results, list)

    if baseline:
        collector = []
        for r in results:
            d = r.as_dict(max_lines=lines)
            d["more_info"] = docs_utils.get_url(d["test_id"])
            if len(results[r]) > 1:
                d["candidates"] = [
                    c.as_dict(max_lines=lines) for c in results[r]
                ]
            collector.append(d)

    else:
        collector = [r.as_dict(max_lines=lines) for r in results]
        for elem in collector:
            elem["more_info"] = docs_utils.get_url(elem["test_id"])

    itemgetter = operator.itemgetter
    if manager.agg_type == "vuln":
        machine_output["results"] = sorted(
            collector, key=itemgetter("test_name")
        )
    else:
        machine_output["results"] = sorted(
            collector, key=itemgetter("filename")
        )

    machine_output["metrics"] = manager.metrics.data

    # timezone agnostic format
    TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

    time_string = datetime.datetime.now(datetime.timezone.utc).strftime(
        TS_FORMAT
    )
    machine_output["generated_at"] = time_string

    result = json.dumps(
        machine_output, sort_keys=True, indent=2, separators=(",", ": ")
    )

    with fileobj:
        fileobj.write(result)

    if fileobj.name != sys.stdout.name:
        LOG.info("JSON output written to file: %s", fileobj.name)
