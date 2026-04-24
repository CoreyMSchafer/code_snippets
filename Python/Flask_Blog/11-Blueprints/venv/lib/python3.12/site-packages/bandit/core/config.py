#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
import logging
import sys

import yaml

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

from bandit.core import constants
from bandit.core import extension_loader
from bandit.core import utils

LOG = logging.getLogger(__name__)


class BanditConfig:
    def __init__(self, config_file=None):
        """Attempt to initialize a config dictionary from a yaml file.

        Error out if loading the yaml file fails for any reason.
        :param config_file: The Bandit yaml config file

        :raises bandit.utils.ConfigError: If the config is invalid or
            unreadable.
        """
        self.config_file = config_file
        self._config = {}

        if config_file:
            try:
                f = open(config_file, "rb")
            except OSError:
                raise utils.ConfigError(
                    "Could not read config file.", config_file
                )

            if config_file.endswith(".toml"):
                if tomllib is None:
                    raise utils.ConfigError(
                        "toml parser not available, reinstall with toml extra",
                        config_file,
                    )

                try:
                    with f:
                        self._config = (
                            tomllib.load(f).get("tool", {}).get("bandit", {})
                        )
                except tomllib.TOMLDecodeError as err:
                    LOG.error(err)
                    raise utils.ConfigError("Error parsing file.", config_file)
            else:
                try:
                    with f:
                        self._config = yaml.safe_load(f)
                except yaml.YAMLError as err:
                    LOG.error(err)
                    raise utils.ConfigError("Error parsing file.", config_file)

            self.validate(config_file)

            # valid config must be a dict
            if not isinstance(self._config, dict):
                raise utils.ConfigError("Error parsing file.", config_file)

            self.convert_legacy_config()

        else:
            # use sane defaults
            self._config["plugin_name_pattern"] = "*.py"
            self._config["include"] = ["*.py", "*.pyw"]

        self._init_settings()

    def get_option(self, option_string):
        """Returns the option from the config specified by the option_string.

        '.' can be used to denote levels, for example to retrieve the options
        from the 'a' profile you can use 'profiles.a'
        :param option_string: The string specifying the option to retrieve
        :return: The object specified by the option_string, or None if it can't
        be found.
        """
        option_levels = option_string.split(".")
        cur_item = self._config
        for level in option_levels:
            if cur_item and (level in cur_item):
                cur_item = cur_item[level]
            else:
                return None

        return cur_item

    def get_setting(self, setting_name):
        if setting_name in self._settings:
            return self._settings[setting_name]
        else:
            return None

    @property
    def config(self):
        """Property to return the config dictionary

        :return: Config dictionary
        """
        return self._config

    def _init_settings(self):
        """This function calls a set of other functions (one per setting)

        This function calls a set of other functions (one per setting) to build
        out the _settings dictionary.  Each other function will set values from
        the config (if set), otherwise use defaults (from constants if
        possible).
        :return: -
        """
        self._settings = {}
        self._init_plugin_name_pattern()

    def _init_plugin_name_pattern(self):
        """Sets settings['plugin_name_pattern'] from default or config file."""
        plugin_name_pattern = constants.plugin_name_pattern
        if self.get_option("plugin_name_pattern"):
            plugin_name_pattern = self.get_option("plugin_name_pattern")
        self._settings["plugin_name_pattern"] = plugin_name_pattern

    def convert_legacy_config(self):
        updated_profiles = self.convert_names_to_ids()
        bad_calls, bad_imports = self.convert_legacy_blacklist_data()

        if updated_profiles:
            self.convert_legacy_blacklist_tests(
                updated_profiles, bad_calls, bad_imports
            )
            self._config["profiles"] = updated_profiles

    def convert_names_to_ids(self):
        """Convert test names to IDs, unknown names are left unchanged."""
        extman = extension_loader.MANAGER

        updated_profiles = {}
        for name, profile in (self.get_option("profiles") or {}).items():
            # NOTE(tkelsey): can't use default of get() because value is
            # sometimes explicitly 'None', for example when the list is given
            # in yaml but not populated with any values.
            include = {
                (extman.get_test_id(i) or i)
                for i in (profile.get("include") or [])
            }
            exclude = {
                (extman.get_test_id(i) or i)
                for i in (profile.get("exclude") or [])
            }
            updated_profiles[name] = {"include": include, "exclude": exclude}
        return updated_profiles

    def convert_legacy_blacklist_data(self):
        """Detect legacy blacklist data and convert it to new format."""
        bad_calls_list = []
        bad_imports_list = []

        bad_calls = self.get_option("blacklist_calls") or {}
        bad_calls = bad_calls.get("bad_name_sets", {})
        for item in bad_calls:
            for key, val in item.items():
                val["name"] = key
                val["message"] = val["message"].replace("{func}", "{name}")
                bad_calls_list.append(val)

        bad_imports = self.get_option("blacklist_imports") or {}
        bad_imports = bad_imports.get("bad_import_sets", {})
        for item in bad_imports:
            for key, val in item.items():
                val["name"] = key
                val["message"] = val["message"].replace("{module}", "{name}")
                val["qualnames"] = val["imports"]
                del val["imports"]
                bad_imports_list.append(val)

        if bad_imports_list or bad_calls_list:
            LOG.warning(
                "Legacy blacklist data found in config, overriding "
                "data plugins"
            )
        return bad_calls_list, bad_imports_list

    @staticmethod
    def convert_legacy_blacklist_tests(profiles, bad_imports, bad_calls):
        """Detect old blacklist tests, convert to use new builtin."""

        def _clean_set(name, data):
            if name in data:
                data.remove(name)
                data.add("B001")

        for name, profile in profiles.items():
            blacklist = {}
            include = profile["include"]
            exclude = profile["exclude"]

            name = "blacklist_calls"
            if name in include and name not in exclude:
                blacklist.setdefault("Call", []).extend(bad_calls)

            _clean_set(name, include)
            _clean_set(name, exclude)

            name = "blacklist_imports"
            if name in include and name not in exclude:
                blacklist.setdefault("Import", []).extend(bad_imports)
                blacklist.setdefault("ImportFrom", []).extend(bad_imports)
                blacklist.setdefault("Call", []).extend(bad_imports)

            _clean_set(name, include)
            _clean_set(name, exclude)
            _clean_set("blacklist_import_func", include)
            _clean_set("blacklist_import_func", exclude)

            # This can happen with a legacy config that includes
            # blacklist_calls but exclude blacklist_imports for example
            if "B001" in include and "B001" in exclude:
                exclude.remove("B001")

            profile["blacklist"] = blacklist

    def validate(self, path):
        """Validate the config data."""
        legacy = False
        message = (
            "Config file has an include or exclude reference "
            "to legacy test '{0}' but no configuration data for "
            "it. Configuration data is required for this test. "
            "Please consider switching to the new config file "
            "format, the tool 'bandit-config-generator' can help "
            "you with this."
        )

        def _test(key, block, exclude, include):
            if key in exclude or key in include:
                if self._config.get(block) is None:
                    raise utils.ConfigError(message.format(key), path)

        if "profiles" in self._config:
            legacy = True
            for profile in self._config["profiles"].values():
                inc = profile.get("include") or set()
                exc = profile.get("exclude") or set()

                _test("blacklist_imports", "blacklist_imports", inc, exc)
                _test("blacklist_import_func", "blacklist_imports", inc, exc)
                _test("blacklist_calls", "blacklist_calls", inc, exc)

        # show deprecation message
        if legacy:
            LOG.warning(
                "Config file '%s' contains deprecated legacy config "
                "data. Please consider upgrading to the new config "
                "format. The tool 'bandit-config-generator' can help "
                "you with this. Support for legacy configs will be "
                "removed in a future bandit version.",
                path,
            )
