#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
import ast

from bandit.core import utils


class Context:
    def __init__(self, context_object=None):
        """Initialize the class with a context, empty dict otherwise

        :param context_object: The context object to create class from
        :return: -
        """
        if context_object is not None:
            self._context = context_object
        else:
            self._context = dict()

    def __repr__(self):
        """Generate representation of object for printing / interactive use

        Most likely only interested in non-default properties, so we return
        the string version of _context.

        Example string returned:
        <Context {'node': <_ast.Call object at 0x110252510>, 'function': None,
        'name': 'socket', 'imports': set(['socket']), 'module': None,
        'filename': 'examples/binding.py',
        'call': <_ast.Call object at 0x110252510>, 'lineno': 3,
        'import_aliases': {}, 'qualname': 'socket.socket'}>

        :return: A string representation of the object
        """
        return f"<Context {self._context}>"

    @property
    def call_args(self):
        """Get a list of function args

        :return: A list of function args
        """
        args = []
        if "call" in self._context and hasattr(self._context["call"], "args"):
            for arg in self._context["call"].args:
                if hasattr(arg, "attr"):
                    args.append(arg.attr)
                else:
                    args.append(self._get_literal_value(arg))
        return args

    @property
    def call_args_count(self):
        """Get the number of args a function call has

        :return: The number of args a function call has or None
        """
        if "call" in self._context and hasattr(self._context["call"], "args"):
            return len(self._context["call"].args)
        else:
            return None

    @property
    def call_function_name(self):
        """Get the name (not FQ) of a function call

        :return: The name (not FQ) of a function call
        """
        return self._context.get("name")

    @property
    def call_function_name_qual(self):
        """Get the FQ name of a function call

        :return: The FQ name of a function call
        """
        return self._context.get("qualname")

    @property
    def call_keywords(self):
        """Get a dictionary of keyword parameters

        :return: A dictionary of keyword parameters for a call as strings
        """
        if "call" in self._context and hasattr(
            self._context["call"], "keywords"
        ):
            return_dict = {}
            for li in self._context["call"].keywords:
                if hasattr(li.value, "attr"):
                    return_dict[li.arg] = li.value.attr
                else:
                    return_dict[li.arg] = self._get_literal_value(li.value)
            return return_dict
        else:
            return None

    @property
    def node(self):
        """Get the raw AST node associated with the context

        :return: The raw AST node associated with the context
        """
        return self._context.get("node")

    @property
    def string_val(self):
        """Get the value of a standalone unicode or string object

        :return: value of a standalone unicode or string object
        """
        return self._context.get("str")

    @property
    def bytes_val(self):
        """Get the value of a standalone bytes object (py3 only)

        :return: value of a standalone bytes object
        """
        return self._context.get("bytes")

    @property
    def string_val_as_escaped_bytes(self):
        """Get escaped value of the object.

        Turn the value of a string or bytes object into byte sequence with
        unknown, control, and \\ characters escaped.

        This function should be used when looking for a known sequence in a
        potentially badly encoded string in the code.

        :return: sequence of printable ascii bytes representing original string
        """
        val = self.string_val
        if val is not None:
            # it's any of str or unicode in py2, or str in py3
            return val.encode("unicode_escape")

        val = self.bytes_val
        if val is not None:
            return utils.escaped_bytes_representation(val)

        return None

    @property
    def statement(self):
        """Get the raw AST for the current statement

        :return: The raw AST for the current statement
        """
        return self._context.get("statement")

    @property
    def function_def_defaults_qual(self):
        """Get a list of fully qualified default values in a function def

        :return: List of defaults
        """
        defaults = []
        if (
            "node" in self._context
            and hasattr(self._context["node"], "args")
            and hasattr(self._context["node"].args, "defaults")
        ):
            for default in self._context["node"].args.defaults:
                defaults.append(
                    utils.get_qual_attr(
                        default, self._context["import_aliases"]
                    )
                )
        return defaults

    def _get_literal_value(self, literal):
        """Utility function to turn AST literals into native Python types

        :param literal: The AST literal to convert
        :return: The value of the AST literal
        """
        if isinstance(literal, ast.Constant):
            if isinstance(literal.value, bool):
                literal_value = str(literal.value)
            elif literal.value is None:
                literal_value = str(literal.value)
            else:
                literal_value = literal.value

        elif isinstance(literal, ast.List):
            return_list = list()
            for li in literal.elts:
                return_list.append(self._get_literal_value(li))
            literal_value = return_list

        elif isinstance(literal, ast.Tuple):
            return_tuple = tuple()
            for ti in literal.elts:
                return_tuple += (self._get_literal_value(ti),)
            literal_value = return_tuple

        elif isinstance(literal, ast.Set):
            return_set = set()
            for si in literal.elts:
                return_set.add(self._get_literal_value(si))
            literal_value = return_set

        elif isinstance(literal, ast.Dict):
            literal_value = dict(zip(literal.keys, literal.values))

        elif isinstance(literal, ast.Name):
            literal_value = literal.id

        else:
            literal_value = None

        return literal_value

    def get_call_arg_value(self, argument_name):
        """Gets the value of a named argument in a function call.

        :return: named argument value
        """
        kwd_values = self.call_keywords
        if kwd_values is not None and argument_name in kwd_values:
            return kwd_values[argument_name]

    def check_call_arg_value(self, argument_name, argument_values=None):
        """Checks for a value of a named argument in a function call.

        Returns none if the specified argument is not found.
        :param argument_name: A string - name of the argument to look for
        :param argument_values: the value, or list of values to test against
        :return: Boolean True if argument found and matched, False if
        found and not matched, None if argument not found at all
        """
        arg_value = self.get_call_arg_value(argument_name)
        if arg_value is not None:
            if not isinstance(argument_values, list):
                # if passed a single value, or a tuple, convert to a list
                argument_values = list((argument_values,))
            for val in argument_values:
                if arg_value == val:
                    return True
            return False
        else:
            # argument name not found, return None to allow testing for this
            # eventuality
            return None

    def get_lineno_for_call_arg(self, argument_name):
        """Get the line number for a specific named argument

        In case the call is split over multiple lines, get the correct one for
        the argument.
        :param argument_name: A string - name of the argument to look for
        :return: Integer - the line number of the found argument, or -1
        """
        if hasattr(self.node, "keywords"):
            for key in self.node.keywords:
                if key.arg == argument_name:
                    return key.value.lineno

    def get_call_arg_at_position(self, position_num):
        """Returns positional argument at the specified position (if it exists)

        :param position_num: The index of the argument to return the value for
        :return: Value of the argument at the specified position if it exists
        """
        max_args = self.call_args_count
        if max_args and position_num < max_args:
            arg = self._context["call"].args[position_num]
            return getattr(arg, "attr", None) or self._get_literal_value(arg)
        else:
            return None

    def is_module_being_imported(self, module):
        """Check for the specified module is currently being imported

        :param module: The module name to look for
        :return: True if the module is found, False otherwise
        """
        return self._context.get("module") == module

    def is_module_imported_exact(self, module):
        """Check if a specified module has been imported; only exact matches.

        :param module: The module name to look for
        :return: True if the module is found, False otherwise
        """
        return module in self._context.get("imports", [])

    def is_module_imported_like(self, module):
        """Check if a specified module has been imported

        Check if a specified module has been imported; specified module exists
        as part of any import statement.
        :param module: The module name to look for
        :return: True if the module is found, False otherwise
        """
        if "imports" in self._context:
            for imp in self._context["imports"]:
                if module in imp:
                    return True
        return False

    @property
    def filename(self):
        return self._context.get("filename")

    @property
    def file_data(self):
        return self._context.get("file_data")

    @property
    def import_aliases(self):
        return self._context.get("import_aliases")
