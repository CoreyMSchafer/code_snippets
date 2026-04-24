#
# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
import collections

from bandit.core import constants


class Metrics:
    """Bandit metric gathering.

    This class is a singleton used to gather and process metrics collected when
    processing a code base with bandit. Metric collection is stateful, that
    is, an active metric block will be set when requested and all subsequent
    operations will effect that metric block until it is replaced by a setting
    a new one.
    """

    def __init__(self):
        self.data = dict()
        self.data["_totals"] = {
            "loc": 0,
            "nosec": 0,
            "skipped_tests": 0,
        }

        # initialize 0 totals for criteria and rank; this will be reset later
        for rank in constants.RANKING:
            for criteria in constants.CRITERIA:
                self.data["_totals"][f"{criteria[0]}.{rank}"] = 0

    def begin(self, fname):
        """Begin a new metric block.

        This starts a new metric collection name "fname" and makes is active.
        :param fname: the metrics unique name, normally the file name.
        """
        self.data[fname] = {
            "loc": 0,
            "nosec": 0,
            "skipped_tests": 0,
        }
        self.current = self.data[fname]

    def note_nosec(self, num=1):
        """Note a "nosec" comment.

        Increment the currently active metrics nosec count.
        :param num: number of nosecs seen, defaults to 1
        """
        self.current["nosec"] += num

    def note_skipped_test(self, num=1):
        """Note a "nosec BXXX, BYYY, ..." comment.

        Increment the currently active metrics skipped_tests count.
        :param num: number of skipped_tests seen, defaults to 1
        """
        self.current["skipped_tests"] += num

    def count_locs(self, lines):
        """Count lines of code.

        We count lines that are not empty and are not comments. The result is
        added to our currently active metrics loc count (normally this is 0).

        :param lines: lines in the file to process
        """

        def proc(line):
            tmp = line.strip()
            return bool(tmp and not tmp.startswith(b"#"))

        self.current["loc"] += sum(proc(line) for line in lines)

    def count_issues(self, scores):
        self.current.update(self._get_issue_counts(scores))

    def aggregate(self):
        """Do final aggregation of metrics."""
        c = collections.Counter()
        for fname in self.data:
            c.update(self.data[fname])
        self.data["_totals"] = dict(c)

    @staticmethod
    def _get_issue_counts(scores):
        """Get issue counts aggregated by confidence/severity rankings.

        :param scores: list of scores to aggregate / count
        :return: aggregated total (count) of issues identified
        """
        issue_counts = {}
        for score in scores:
            for criteria, _ in constants.CRITERIA:
                for i, rank in enumerate(constants.RANKING):
                    label = f"{criteria}.{rank}"
                    if label not in issue_counts:
                        issue_counts[label] = 0
                        count = (
                            score[criteria][i]
                            // constants.RANKING_VALUES[rank]
                        )
                        issue_counts[label] += count
        return issue_counts
