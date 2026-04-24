#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
import collections
import fnmatch
import io
import json
import logging
import os
import re
import sys
import tokenize
import traceback

from rich import progress

from bandit.core import constants as b_constants
from bandit.core import extension_loader
from bandit.core import issue
from bandit.core import meta_ast as b_meta_ast
from bandit.core import metrics
from bandit.core import node_visitor as b_node_visitor
from bandit.core import test_set as b_test_set

LOG = logging.getLogger(__name__)
NOSEC_COMMENT = re.compile(r"#\s*nosec:?\s*(?P<tests>[^#]+)?#?")
NOSEC_COMMENT_TESTS = re.compile(r"(?:(B\d+|[a-z\d_]+),?)+", re.IGNORECASE)
PROGRESS_THRESHOLD = 50


class BanditManager:
    scope = []

    def __init__(
        self,
        config,
        agg_type,
        debug=False,
        verbose=False,
        quiet=False,
        profile=None,
        ignore_nosec=False,
    ):
        """Get logger, config, AST handler, and result store ready

        :param config: config options object
        :type config: bandit.core.BanditConfig
        :param agg_type: aggregation type
        :param debug: Whether to show debug messages or not
        :param verbose: Whether to show verbose output
        :param quiet: Whether to only show output in the case of an error
        :param profile_name: Optional name of profile to use (from cmd line)
        :param ignore_nosec: Whether to ignore #nosec or not
        :return:
        """
        self.debug = debug
        self.verbose = verbose
        self.quiet = quiet
        if not profile:
            profile = {}
        self.ignore_nosec = ignore_nosec
        self.b_conf = config
        self.files_list = []
        self.excluded_files = []
        self.b_ma = b_meta_ast.BanditMetaAst()
        self.skipped = []
        self.results = []
        self.baseline = []
        self.agg_type = agg_type
        self.metrics = metrics.Metrics()
        self.b_ts = b_test_set.BanditTestSet(config, profile)
        self.scores = []

    def get_skipped(self):
        ret = []
        # "skip" is a tuple of name and reason, decode just the name
        for skip in self.skipped:
            if isinstance(skip[0], bytes):
                ret.append((skip[0].decode("utf-8"), skip[1]))
            else:
                ret.append(skip)
        return ret

    def get_issue_list(
        self, sev_level=b_constants.LOW, conf_level=b_constants.LOW
    ):
        return self.filter_results(sev_level, conf_level)

    def populate_baseline(self, data):
        """Populate a baseline set of issues from a JSON report

        This will populate a list of baseline issues discovered from a previous
        run of bandit. Later this baseline can be used to filter out the result
        set, see filter_results.
        """
        items = []
        try:
            jdata = json.loads(data)
            items = [issue.issue_from_dict(j) for j in jdata["results"]]
        except Exception as e:
            LOG.warning("Failed to load baseline data: %s", e)
        self.baseline = items

    def filter_results(self, sev_filter, conf_filter):
        """Returns a list of results filtered by the baseline

        This works by checking the number of results returned from each file we
        process. If the number of results is different to the number reported
        for the same file in the baseline, then we return all results for the
        file. We can't reliably return just the new results, as line numbers
        will likely have changed.

        :param sev_filter: severity level filter to apply
        :param conf_filter: confidence level filter to apply
        """

        results = [
            i for i in self.results if i.filter(sev_filter, conf_filter)
        ]

        if not self.baseline:
            return results

        unmatched = _compare_baseline_results(self.baseline, results)
        # if it's a baseline we'll return a dictionary of issues and a list of
        # candidate issues
        return _find_candidate_matches(unmatched, results)

    def results_count(
        self, sev_filter=b_constants.LOW, conf_filter=b_constants.LOW
    ):
        """Return the count of results

        :param sev_filter: Severity level to filter lower
        :param conf_filter: Confidence level to filter
        :return: Number of results in the set
        """
        return len(self.get_issue_list(sev_filter, conf_filter))

    def output_results(
        self,
        lines,
        sev_level,
        conf_level,
        output_file,
        output_format,
        template=None,
    ):
        """Outputs results from the result store

        :param lines: How many surrounding lines to show per result
        :param sev_level: Which severity levels to show (LOW, MEDIUM, HIGH)
        :param conf_level: Which confidence levels to show (LOW, MEDIUM, HIGH)
        :param output_file: File to store results
        :param output_format: output format plugin name
        :param template: Output template with non-terminal tags <N>
                         (default:  {abspath}:{line}:
                         {test_id}[bandit]: {severity}: {msg})
        :return: -
        """
        try:
            formatters_mgr = extension_loader.MANAGER.formatters_mgr
            if output_format not in formatters_mgr:
                output_format = (
                    "screen"
                    if (
                        sys.stdout.isatty()
                        and os.getenv("NO_COLOR") is None
                        and os.getenv("TERM") != "dumb"
                    )
                    else "txt"
                )

            formatter = formatters_mgr[output_format]
            report_func = formatter.plugin
            if output_format == "custom":
                report_func(
                    self,
                    fileobj=output_file,
                    sev_level=sev_level,
                    conf_level=conf_level,
                    template=template,
                )
            else:
                report_func(
                    self,
                    fileobj=output_file,
                    sev_level=sev_level,
                    conf_level=conf_level,
                    lines=lines,
                )

        except Exception as e:
            raise RuntimeError(
                f"Unable to output report using "
                f"'{output_format}' formatter: {str(e)}"
            )

    def discover_files(self, targets, recursive=False, excluded_paths=""):
        """Add tests directly and from a directory to the test set

        :param targets: The command line list of files and directories
        :param recursive: True/False - whether to add all files from dirs
        :return:
        """
        # We'll maintain a list of files which are added, and ones which have
        # been explicitly excluded
        files_list = set()
        excluded_files = set()

        excluded_path_globs = self.b_conf.get_option("exclude_dirs") or []
        included_globs = self.b_conf.get_option("include") or ["*.py"]

        # if there are command line provided exclusions add them to the list
        if excluded_paths:
            for path in excluded_paths.split(","):
                if os.path.isdir(path):
                    path = os.path.join(path, "*")

                excluded_path_globs.append(path)

        # build list of files we will analyze
        for fname in targets:
            # if this is a directory and recursive is set, find all files
            if os.path.isdir(fname):
                if recursive:
                    new_files, newly_excluded = _get_files_from_dir(
                        fname,
                        included_globs=included_globs,
                        excluded_path_strings=excluded_path_globs,
                    )
                    files_list.update(new_files)
                    excluded_files.update(newly_excluded)
                else:
                    LOG.warning(
                        "Skipping directory (%s), use -r flag to "
                        "scan contents",
                        fname,
                    )

            else:
                # if the user explicitly mentions a file on command line,
                # we'll scan it, regardless of whether it's in the included
                # file types list
                if _is_file_included(
                    fname,
                    included_globs,
                    excluded_path_globs,
                    enforce_glob=False,
                ):
                    if fname != "-":
                        fname = os.path.join(".", fname)
                    files_list.add(fname)
                else:
                    excluded_files.add(fname)

        self.files_list = sorted(files_list)
        self.excluded_files = sorted(excluded_files)

    def run_tests(self):
        """Runs through all files in the scope

        :return: -
        """
        # if we have problems with a file, we'll remove it from the files_list
        # and add it to the skipped list instead
        new_files_list = list(self.files_list)
        if (
            len(self.files_list) > PROGRESS_THRESHOLD
            and LOG.getEffectiveLevel() <= logging.INFO
        ):
            files = progress.track(self.files_list)
        else:
            files = self.files_list

        for count, fname in enumerate(files):
            LOG.debug("working on file : %s", fname)

            try:
                if fname == "-":
                    open_fd = os.fdopen(sys.stdin.fileno(), "rb", 0)
                    fdata = io.BytesIO(open_fd.read())
                    new_files_list = [
                        "<stdin>" if x == "-" else x for x in new_files_list
                    ]
                    self._parse_file("<stdin>", fdata, new_files_list)
                else:
                    with open(fname, "rb") as fdata:
                        self._parse_file(fname, fdata, new_files_list)
            except OSError as e:
                self.skipped.append((fname, e.strerror))
                new_files_list.remove(fname)

        # reflect any files which may have been skipped
        self.files_list = new_files_list

        # do final aggregation of metrics
        self.metrics.aggregate()

    def _parse_file(self, fname, fdata, new_files_list):
        try:
            # parse the current file
            data = fdata.read()
            lines = data.splitlines()
            self.metrics.begin(fname)
            self.metrics.count_locs(lines)
            # nosec_lines is a dict of line number -> set of tests to ignore
            #                                         for the line
            nosec_lines = dict()
            try:
                fdata.seek(0)
                tokens = tokenize.tokenize(fdata.readline)

                if not self.ignore_nosec:
                    for toktype, tokval, (lineno, _), _, _ in tokens:
                        if toktype == tokenize.COMMENT:
                            nosec_lines[lineno] = _parse_nosec_comment(tokval)

            except tokenize.TokenError:
                pass
            score = self._execute_ast_visitor(fname, fdata, data, nosec_lines)
            self.scores.append(score)
            self.metrics.count_issues([score])
        except KeyboardInterrupt:
            sys.exit(2)
        except SyntaxError:
            self.skipped.append(
                (fname, "syntax error while parsing AST from file")
            )
            new_files_list.remove(fname)
        except Exception as e:
            LOG.error(
                "Exception occurred when executing tests against %s.", fname
            )
            if not LOG.isEnabledFor(logging.DEBUG):
                LOG.error(
                    'Run "bandit --debug %s" to see the full traceback.', fname
                )

            self.skipped.append((fname, "exception while scanning file"))
            new_files_list.remove(fname)
            LOG.debug("  Exception string: %s", e)
            LOG.debug("  Exception traceback: %s", traceback.format_exc())

    def _execute_ast_visitor(self, fname, fdata, data, nosec_lines):
        """Execute AST parse on each file

        :param fname: The name of the file being parsed
        :param data: Original file contents
        :param lines: The lines of code to process
        :return: The accumulated test score
        """
        score = []
        res = b_node_visitor.BanditNodeVisitor(
            fname,
            fdata,
            self.b_ma,
            self.b_ts,
            self.debug,
            nosec_lines,
            self.metrics,
        )

        score = res.process(data)
        self.results.extend(res.tester.results)
        return score


def _get_files_from_dir(
    files_dir, included_globs=None, excluded_path_strings=None
):
    if not included_globs:
        included_globs = ["*.py"]
    if not excluded_path_strings:
        excluded_path_strings = []

    files_list = set()
    excluded_files = set()

    for root, _, files in os.walk(files_dir):
        for filename in files:
            path = os.path.join(root, filename)
            if _is_file_included(path, included_globs, excluded_path_strings):
                files_list.add(path)
            else:
                excluded_files.add(path)

    return files_list, excluded_files


def _is_file_included(
    path, included_globs, excluded_path_strings, enforce_glob=True
):
    """Determine if a file should be included based on filename

    This utility function determines if a file should be included based
    on the file name, a list of parsed extensions, excluded paths, and a flag
    specifying whether extensions should be enforced.

    :param path: Full path of file to check
    :param parsed_extensions: List of parsed extensions
    :param excluded_paths: List of paths (globbing supported) from which we
        should not include files
    :param enforce_glob: Can set to false to bypass extension check
    :return: Boolean indicating whether a file should be included
    """
    return_value = False

    # if this is matches a glob of files we look at, and it isn't in an
    # excluded path
    if _matches_glob_list(path, included_globs) or not enforce_glob:
        if not _matches_glob_list(path, excluded_path_strings) and not any(
            x in path for x in excluded_path_strings
        ):
            return_value = True

    return return_value


def _matches_glob_list(filename, glob_list):
    for glob in glob_list:
        if fnmatch.fnmatch(filename, glob):
            return True
    return False


def _compare_baseline_results(baseline, results):
    """Compare a baseline list of issues to list of results

    This function compares a baseline set of issues to a current set of issues
    to find results that weren't present in the baseline.

    :param baseline: Baseline list of issues
    :param results: Current list of issues
    :return: List of unmatched issues
    """
    return [a for a in results if a not in baseline]


def _find_candidate_matches(unmatched_issues, results_list):
    """Returns a dictionary with issue candidates

    For example, let's say we find a new command injection issue in a file
    which used to have two.  Bandit can't tell which of the command injection
    issues in the file are new, so it will show all three.  The user should
    be able to pick out the new one.

    :param unmatched_issues: List of issues that weren't present before
    :param results_list: main list of current Bandit findings
    :return: A dictionary with a list of candidates for each issue
    """

    issue_candidates = collections.OrderedDict()

    for unmatched in unmatched_issues:
        issue_candidates[unmatched] = [
            i for i in results_list if unmatched == i
        ]

    return issue_candidates


def _find_test_id_from_nosec_string(extman, match):
    test_id = extman.check_id(match)
    if test_id:
        return match
    # Finding by short_id didn't work, let's check the test name
    test_id = extman.get_test_id(match)
    if not test_id:
        # Name and short id didn't work:
        LOG.warning(
            "Test in comment: %s is not a test name or id, ignoring", match
        )
    return test_id  # We want to return None or the string here regardless


def _parse_nosec_comment(comment):
    found_no_sec_comment = NOSEC_COMMENT.search(comment)
    if not found_no_sec_comment:
        # there was no nosec comment
        return None

    matches = found_no_sec_comment.groupdict()
    nosec_tests = matches.get("tests", set())

    # empty set indicates that there was a nosec comment without specific
    # test ids or names
    test_ids = set()
    if nosec_tests:
        extman = extension_loader.MANAGER
        # lookup tests by short code or name
        for test in NOSEC_COMMENT_TESTS.finditer(nosec_tests):
            test_match = test.group(1)
            test_id = _find_test_id_from_nosec_string(extman, test_match)
            if test_id:
                test_ids.add(test_id)

    return test_ids
