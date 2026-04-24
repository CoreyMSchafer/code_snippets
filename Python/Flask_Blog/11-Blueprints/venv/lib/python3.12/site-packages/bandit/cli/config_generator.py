# Copyright 2015 Red Hat Inc.
#
# SPDX-License-Identifier: Apache-2.0
"""Bandit is a tool designed to find common security issues in Python code."""
import argparse
import importlib
import logging
import os
import sys

import yaml

from bandit.core import extension_loader

PROG_NAME = "bandit_conf_generator"
LOG = logging.getLogger(__name__)


template = """
### Bandit config file generated from:
# '{cli}'

### This config may optionally select a subset of tests to run or skip by
### filling out the 'tests' and 'skips' lists given below. If no tests are
### specified for inclusion then it is assumed all tests are desired. The skips
### set will remove specific tests from the include set. This can be controlled
### using the -t/-s CLI options. Note that the same test ID should not appear
### in both 'tests' and 'skips', this would be nonsensical and is detected by
### Bandit at runtime.

# Available tests:
{test_list}

# (optional) list included test IDs here, eg '[B101, B406]':
{test}

# (optional) list skipped test IDs here, eg '[B101, B406]':
{skip}

### (optional) plugin settings - some test plugins require configuration data
### that may be given here, per-plugin. All bandit test plugins have a built in
### set of sensible defaults and these will be used if no configuration is
### provided. It is not necessary to provide settings for every (or any) plugin
### if the defaults are acceptable.

{settings}
"""


def init_logger():
    """Init logger."""
    LOG.handlers = []
    log_level = logging.INFO
    log_format_string = "[%(levelname)5s]: %(message)s"
    logging.captureWarnings(True)
    LOG.setLevel(log_level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(log_format_string))
    LOG.addHandler(handler)


def parse_args():
    """Parse arguments."""
    help_description = """Bandit Config Generator

    This tool is used to generate an optional profile.  The profile may be used
    to include or skip tests and override values for plugins.

    When used to store an output profile, this tool will output a template that
    includes all plugins and their default settings.  Any settings which aren't
    being overridden can be safely removed from the profile and default values
    will be used.  Bandit will prefer settings from the profile over the built
    in values."""

    parser = argparse.ArgumentParser(
        description=help_description,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    if sys.version_info >= (3, 14):
        parser.suggest_on_error = True
        parser.color = False

    parser.add_argument(
        "--show-defaults",
        dest="show_defaults",
        action="store_true",
        help="show the default settings values for each "
        "plugin but do not output a profile",
    )
    parser.add_argument(
        "-o",
        "--out",
        dest="output_file",
        action="store",
        help="output file to save profile",
    )
    parser.add_argument(
        "-t",
        "--tests",
        dest="tests",
        action="store",
        default=None,
        type=str,
        help="list of test names to run",
    )
    parser.add_argument(
        "-s",
        "--skip",
        dest="skips",
        action="store",
        default=None,
        type=str,
        help="list of test names to skip",
    )
    args = parser.parse_args()

    if not args.output_file and not args.show_defaults:
        parser.print_help()
        parser.exit(1)

    return args


def get_config_settings():
    """Get configuration settings."""
    config = {}
    for plugin in extension_loader.MANAGER.plugins:
        fn_name = plugin.name
        function = plugin.plugin

        # if a function takes config...
        if hasattr(function, "_takes_config"):
            fn_module = importlib.import_module(function.__module__)

            # call the config generator if it exists
            if hasattr(fn_module, "gen_config"):
                config[fn_name] = fn_module.gen_config(function._takes_config)

    return yaml.safe_dump(config, default_flow_style=False)


def main():
    """Config generator to write configuration file."""
    init_logger()
    args = parse_args()

    yaml_settings = get_config_settings()

    if args.show_defaults:
        print(yaml_settings)

    if args.output_file:
        if os.path.exists(os.path.abspath(args.output_file)):
            LOG.error("File %s already exists, exiting", args.output_file)
            sys.exit(2)

        try:
            with open(args.output_file, "w") as f:
                skips = args.skips.split(",") if args.skips else []
                tests = args.tests.split(",") if args.tests else []

                for skip in skips:
                    if not extension_loader.MANAGER.check_id(skip):
                        raise RuntimeError(f"unknown ID in skips: {skip}")

                for test in tests:
                    if not extension_loader.MANAGER.check_id(test):
                        raise RuntimeError(f"unknown ID in tests: {test}")

                tpl = "# {0} : {1}"
                test_list = [
                    tpl.format(t.plugin._test_id, t.name)
                    for t in extension_loader.MANAGER.plugins
                ]

                others = [
                    tpl.format(k, v["name"])
                    for k, v in (
                        extension_loader.MANAGER.blacklist_by_id.items()
                    )
                ]
                test_list.extend(others)
                test_list.sort()

                contents = template.format(
                    cli=" ".join(sys.argv),
                    settings=yaml_settings,
                    test_list="\n".join(test_list),
                    skip="skips: " + str(skips) if skips else "skips:",
                    test="tests: " + str(tests) if tests else "tests:",
                )
                f.write(contents)

        except OSError:
            LOG.error("Unable to open %s for writing", args.output_file)

        except Exception as e:
            LOG.error("Error: %s", e)

        else:
            LOG.info("Successfully wrote profile: %s", args.output_file)

    return 0


if __name__ == "__main__":
    sys.exit(main())
