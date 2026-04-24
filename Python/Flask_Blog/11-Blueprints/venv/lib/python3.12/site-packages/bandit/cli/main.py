#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
"""Bandit is a tool designed to find common security issues in Python code."""
import argparse
import fnmatch
import logging
import os
import sys
import textwrap

import bandit
from bandit.core import config as b_config
from bandit.core import constants
from bandit.core import manager as b_manager
from bandit.core import utils

BASE_CONFIG = "bandit.yaml"
LOG = logging.getLogger()


def _init_logger(log_level=logging.INFO, log_format=None):
    """Initialize the logger.

    :param debug: Whether to enable debug mode
    :return: An instantiated logging instance
    """
    LOG.handlers = []

    if not log_format:
        # default log format
        log_format_string = constants.log_format_string
    else:
        log_format_string = log_format

    logging.captureWarnings(True)

    LOG.setLevel(log_level)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(log_format_string))
    LOG.addHandler(handler)
    LOG.debug("logging initialized")


def _get_options_from_ini(ini_path, target):
    """Return a dictionary of config options or None if we can't load any."""
    ini_file = None

    if ini_path:
        ini_file = ini_path
    else:
        bandit_files = []

        for t in target:
            for root, _, filenames in os.walk(t):
                for filename in fnmatch.filter(filenames, ".bandit"):
                    bandit_files.append(os.path.join(root, filename))

        if len(bandit_files) > 1:
            LOG.error(
                "Multiple .bandit files found - scan separately or "
                "choose one with --ini\n\t%s",
                ", ".join(bandit_files),
            )
            sys.exit(2)

        elif len(bandit_files) == 1:
            ini_file = bandit_files[0]
            LOG.info("Found project level .bandit file: %s", bandit_files[0])

    if ini_file:
        return utils.parse_ini_file(ini_file)
    else:
        return None


def _init_extensions():
    from bandit.core import extension_loader as ext_loader

    return ext_loader.MANAGER


def _log_option_source(default_val, arg_val, ini_val, option_name):
    """It's useful to show the source of each option."""
    # When default value is not defined, arg_val and ini_val is deterministic
    if default_val is None:
        if arg_val:
            LOG.info("Using command line arg for %s", option_name)
            return arg_val
        elif ini_val:
            LOG.info("Using ini file for %s", option_name)
            return ini_val
        else:
            return None
    # No value passed to command line and default value is used
    elif default_val == arg_val:
        return ini_val if ini_val else arg_val
    # Certainly a value is passed to command line
    else:
        return arg_val


def _running_under_virtualenv():
    if hasattr(sys, "real_prefix"):
        return True
    elif sys.prefix != getattr(sys, "base_prefix", sys.prefix):
        return True


def _get_profile(config, profile_name, config_path):
    profile = {}
    if profile_name:
        profiles = config.get_option("profiles") or {}
        profile = profiles.get(profile_name)
        if profile is None:
            raise utils.ProfileNotFound(config_path, profile_name)
        LOG.debug("read in legacy profile '%s': %s", profile_name, profile)
    else:
        profile["include"] = set(config.get_option("tests") or [])
        profile["exclude"] = set(config.get_option("skips") or [])
    return profile


def _log_info(args, profile):
    inc = ",".join([t for t in profile["include"]]) or "None"
    exc = ",".join([t for t in profile["exclude"]]) or "None"
    LOG.info("profile include tests: %s", inc)
    LOG.info("profile exclude tests: %s", exc)
    LOG.info("cli include tests: %s", args.tests)
    LOG.info("cli exclude tests: %s", args.skips)


def main():
    """Bandit CLI."""
    # bring our logging stuff up as early as possible
    debug = (
        logging.DEBUG
        if "-d" in sys.argv or "--debug" in sys.argv
        else logging.INFO
    )
    _init_logger(debug)
    extension_mgr = _init_extensions()

    baseline_formatters = [
        f.name
        for f in filter(
            lambda x: hasattr(x.plugin, "_accepts_baseline"),
            extension_mgr.formatters,
        )
    ]

    # now do normal startup
    parser = argparse.ArgumentParser(
        description="Bandit - a Python source code security analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    if sys.version_info >= (3, 14):
        parser.suggest_on_error = True
        parser.color = False

    parser.add_argument(
        "targets",
        metavar="targets",
        type=str,
        nargs="*",
        help="source file(s) or directory(s) to be tested",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        dest="recursive",
        action="store_true",
        help="find and process files in subdirectories",
    )
    parser.add_argument(
        "-a",
        "--aggregate",
        dest="agg_type",
        action="store",
        default="file",
        type=str,
        choices=["file", "vuln"],
        help="aggregate output by vulnerability (default) or by filename",
    )
    parser.add_argument(
        "-n",
        "--number",
        dest="context_lines",
        action="store",
        default=3,
        type=int,
        help="maximum number of code lines to output for each issue",
    )
    parser.add_argument(
        "-c",
        "--configfile",
        dest="config_file",
        action="store",
        default=None,
        type=str,
        help="optional config file to use for selecting plugins and "
        "overriding defaults",
    )
    parser.add_argument(
        "-p",
        "--profile",
        dest="profile",
        action="store",
        default=None,
        type=str,
        help="profile to use (defaults to executing all tests)",
    )
    parser.add_argument(
        "-t",
        "--tests",
        dest="tests",
        action="store",
        default=None,
        type=str,
        help="comma-separated list of test IDs to run",
    )
    parser.add_argument(
        "-s",
        "--skip",
        dest="skips",
        action="store",
        default=None,
        type=str,
        help="comma-separated list of test IDs to skip",
    )
    severity_group = parser.add_mutually_exclusive_group(required=False)
    severity_group.add_argument(
        "-l",
        "--level",
        dest="severity",
        action="count",
        default=1,
        help="report only issues of a given severity level or "
        "higher (-l for LOW, -ll for MEDIUM, -lll for HIGH)",
    )
    severity_group.add_argument(
        "--severity-level",
        dest="severity_string",
        action="store",
        help="report only issues of a given severity level or higher."
        ' "all" and "low" are likely to produce the same results, but it'
        " is possible for rules to be undefined which will"
        ' not be listed in "low".',
        choices=["all", "low", "medium", "high"],
    )
    confidence_group = parser.add_mutually_exclusive_group(required=False)
    confidence_group.add_argument(
        "-i",
        "--confidence",
        dest="confidence",
        action="count",
        default=1,
        help="report only issues of a given confidence level or "
        "higher (-i for LOW, -ii for MEDIUM, -iii for HIGH)",
    )
    confidence_group.add_argument(
        "--confidence-level",
        dest="confidence_string",
        action="store",
        help="report only issues of a given confidence level or higher."
        ' "all" and "low" are likely to produce the same results, but it'
        " is possible for rules to be undefined which will"
        ' not be listed in "low".',
        choices=["all", "low", "medium", "high"],
    )
    output_format = (
        "screen"
        if (
            sys.stdout.isatty()
            and os.getenv("NO_COLOR") is None
            and os.getenv("TERM") != "dumb"
        )
        else "txt"
    )
    parser.add_argument(
        "-f",
        "--format",
        dest="output_format",
        action="store",
        default=output_format,
        help="specify output format",
        choices=sorted(extension_mgr.formatter_names),
    )
    parser.add_argument(
        "--msg-template",
        action="store",
        default=None,
        help="specify output message template"
        " (only usable with --format custom),"
        " see CUSTOM FORMAT section"
        " for list of available values",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_file",
        action="store",
        nargs="?",
        type=argparse.FileType("w", encoding="utf-8"),
        default=sys.stdout,
        help="write report to filename",
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        help="output extra information like excluded and included files",
    )
    parser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        help="turn on debug mode",
    )
    group.add_argument(
        "-q",
        "--quiet",
        "--silent",
        dest="quiet",
        action="store_true",
        help="only show output in the case of an error",
    )
    parser.add_argument(
        "--ignore-nosec",
        dest="ignore_nosec",
        action="store_true",
        help="do not skip lines with # nosec comments",
    )
    parser.add_argument(
        "-x",
        "--exclude",
        dest="excluded_paths",
        action="store",
        default=",".join(constants.EXCLUDE),
        help="comma-separated list of paths (glob patterns "
        "supported) to exclude from scan "
        "(note that these are in addition to the excluded "
        "paths provided in the config file) (default: "
        + ",".join(constants.EXCLUDE)
        + ")",
    )
    parser.add_argument(
        "-b",
        "--baseline",
        dest="baseline",
        action="store",
        default=None,
        help="path of a baseline report to compare against "
        "(only JSON-formatted files are accepted)",
    )
    parser.add_argument(
        "--ini",
        dest="ini_path",
        action="store",
        default=None,
        help="path to a .bandit file that supplies command line arguments",
    )
    parser.add_argument(
        "--exit-zero",
        action="store_true",
        dest="exit_zero",
        default=False,
        help="exit with 0, " "even with results found",
    )
    python_ver = sys.version.replace("\n", "")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {bandit.__version__}\n"
        f"  python version = {python_ver}",
    )

    parser.set_defaults(debug=False)
    parser.set_defaults(verbose=False)
    parser.set_defaults(quiet=False)
    parser.set_defaults(ignore_nosec=False)

    plugin_info = [
        f"{a[0]}\t{a[1].name}" for a in extension_mgr.plugins_by_id.items()
    ]
    blacklist_info = []
    for a in extension_mgr.blacklist.items():
        for b in a[1]:
            blacklist_info.append(f"{b['id']}\t{b['name']}")

    plugin_list = "\n\t".join(sorted(set(plugin_info + blacklist_info)))
    dedent_text = textwrap.dedent(
        """
    CUSTOM FORMATTING
    -----------------

    Available tags:

        {abspath}, {relpath}, {line}, {col}, {test_id},
        {severity}, {msg}, {confidence}, {range}

    Example usage:

        Default template:
        bandit -r examples/ --format custom --msg-template \\
        "{abspath}:{line}: {test_id}[bandit]: {severity}: {msg}"

        Provides same output as:
        bandit -r examples/ --format custom

        Tags can also be formatted in python string.format() style:
        bandit -r examples/ --format custom --msg-template \\
        "{relpath:20.20s}: {line:03}: {test_id:^8}: DEFECT: {msg:>20}"

        See python documentation for more information about formatting style:
        https://docs.python.org/3/library/string.html

    The following tests were discovered and loaded:
    -----------------------------------------------
    """
    )
    parser.epilog = dedent_text + f"\t{plugin_list}"

    # setup work - parse arguments, and initialize BanditManager
    args = parser.parse_args()
    # Check if `--msg-template` is not present without custom formatter
    if args.output_format != "custom" and args.msg_template is not None:
        parser.error("--msg-template can only be used with --format=custom")

    # Check if confidence or severity level have been specified with strings
    if args.severity_string is not None:
        if args.severity_string == "all":
            args.severity = 1
        elif args.severity_string == "low":
            args.severity = 2
        elif args.severity_string == "medium":
            args.severity = 3
        elif args.severity_string == "high":
            args.severity = 4
        # Other strings will be blocked by argparse

    if args.confidence_string is not None:
        if args.confidence_string == "all":
            args.confidence = 1
        elif args.confidence_string == "low":
            args.confidence = 2
        elif args.confidence_string == "medium":
            args.confidence = 3
        elif args.confidence_string == "high":
            args.confidence = 4
        # Other strings will be blocked by argparse

    # Handle .bandit files in projects to pass cmdline args from file
    ini_options = _get_options_from_ini(args.ini_path, args.targets)
    if ini_options:
        # prefer command line, then ini file
        args.config_file = _log_option_source(
            parser.get_default("configfile"),
            args.config_file,
            ini_options.get("configfile"),
            "config file",
        )

        args.excluded_paths = _log_option_source(
            parser.get_default("excluded_paths"),
            args.excluded_paths,
            ini_options.get("exclude"),
            "excluded paths",
        )

        args.skips = _log_option_source(
            parser.get_default("skips"),
            args.skips,
            ini_options.get("skips"),
            "skipped tests",
        )

        args.tests = _log_option_source(
            parser.get_default("tests"),
            args.tests,
            ini_options.get("tests"),
            "selected tests",
        )

        ini_targets = ini_options.get("targets")
        if ini_targets:
            ini_targets = ini_targets.split(",")

        args.targets = _log_option_source(
            parser.get_default("targets"),
            args.targets,
            ini_targets,
            "selected targets",
        )

        # TODO(tmcpeak): any other useful options to pass from .bandit?

        args.recursive = _log_option_source(
            parser.get_default("recursive"),
            args.recursive,
            ini_options.get("recursive"),
            "recursive scan",
        )

        args.agg_type = _log_option_source(
            parser.get_default("agg_type"),
            args.agg_type,
            ini_options.get("aggregate"),
            "aggregate output type",
        )

        args.context_lines = _log_option_source(
            parser.get_default("context_lines"),
            args.context_lines,
            int(ini_options.get("number") or 0) or None,
            "max code lines output for issue",
        )

        args.profile = _log_option_source(
            parser.get_default("profile"),
            args.profile,
            ini_options.get("profile"),
            "profile",
        )

        args.severity = _log_option_source(
            parser.get_default("severity"),
            args.severity,
            ini_options.get("level"),
            "severity level",
        )

        args.confidence = _log_option_source(
            parser.get_default("confidence"),
            args.confidence,
            ini_options.get("confidence"),
            "confidence level",
        )

        args.output_format = _log_option_source(
            parser.get_default("output_format"),
            args.output_format,
            ini_options.get("format"),
            "output format",
        )

        args.msg_template = _log_option_source(
            parser.get_default("msg_template"),
            args.msg_template,
            ini_options.get("msg-template"),
            "output message template",
        )

        args.output_file = _log_option_source(
            parser.get_default("output_file"),
            args.output_file,
            ini_options.get("output"),
            "output file",
        )

        args.verbose = _log_option_source(
            parser.get_default("verbose"),
            args.verbose,
            ini_options.get("verbose"),
            "output extra information",
        )

        args.debug = _log_option_source(
            parser.get_default("debug"),
            args.debug,
            ini_options.get("debug"),
            "debug mode",
        )

        args.quiet = _log_option_source(
            parser.get_default("quiet"),
            args.quiet,
            ini_options.get("quiet"),
            "silent mode",
        )

        args.ignore_nosec = _log_option_source(
            parser.get_default("ignore_nosec"),
            args.ignore_nosec,
            ini_options.get("ignore-nosec"),
            "do not skip lines with # nosec",
        )

        args.baseline = _log_option_source(
            parser.get_default("baseline"),
            args.baseline,
            ini_options.get("baseline"),
            "path of a baseline report",
        )

    try:
        b_conf = b_config.BanditConfig(config_file=args.config_file)
    except utils.ConfigError as e:
        LOG.error(e)
        sys.exit(2)

    if not args.targets:
        parser.print_usage()
        sys.exit(2)

    # if the log format string was set in the options, reinitialize
    if b_conf.get_option("log_format"):
        log_format = b_conf.get_option("log_format")
        _init_logger(log_level=logging.DEBUG, log_format=log_format)

    if args.quiet:
        _init_logger(log_level=logging.WARN)

    try:
        profile = _get_profile(b_conf, args.profile, args.config_file)
        _log_info(args, profile)

        profile["include"].update(args.tests.split(",") if args.tests else [])
        profile["exclude"].update(args.skips.split(",") if args.skips else [])
        extension_mgr.validate_profile(profile)

    except (utils.ProfileNotFound, ValueError) as e:
        LOG.error(e)
        sys.exit(2)

    b_mgr = b_manager.BanditManager(
        b_conf,
        args.agg_type,
        args.debug,
        profile=profile,
        verbose=args.verbose,
        quiet=args.quiet,
        ignore_nosec=args.ignore_nosec,
    )

    if args.baseline is not None:
        try:
            with open(args.baseline) as bl:
                data = bl.read()
                b_mgr.populate_baseline(data)
        except OSError:
            LOG.warning("Could not open baseline report: %s", args.baseline)
            sys.exit(2)

        if args.output_format not in baseline_formatters:
            LOG.warning(
                "Baseline must be used with one of the following "
                "formats: " + str(baseline_formatters)
            )
            sys.exit(2)

    if args.output_format != "json":
        if args.config_file:
            LOG.info("using config: %s", args.config_file)

        LOG.info(
            "running on Python %d.%d.%d",
            sys.version_info.major,
            sys.version_info.minor,
            sys.version_info.micro,
        )

    # initiate file discovery step within Bandit Manager
    b_mgr.discover_files(args.targets, args.recursive, args.excluded_paths)

    if not b_mgr.b_ts.tests:
        LOG.error("No tests would be run, please check the profile.")
        sys.exit(2)

    # initiate execution of tests within Bandit Manager
    b_mgr.run_tests()
    LOG.debug(b_mgr.b_ma)
    LOG.debug(b_mgr.metrics)

    # trigger output of results by Bandit Manager
    sev_level = constants.RANKING[args.severity - 1]
    conf_level = constants.RANKING[args.confidence - 1]
    b_mgr.output_results(
        args.context_lines,
        sev_level,
        conf_level,
        args.output_file,
        args.output_format,
        args.msg_template,
    )

    if (
        b_mgr.results_count(sev_filter=sev_level, conf_filter=conf_level) > 0
        and not args.exit_zero
    ):
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
